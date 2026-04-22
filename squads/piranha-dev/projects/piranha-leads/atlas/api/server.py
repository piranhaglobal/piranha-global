import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Resolve paths
BASE_DIR = Path(__file__).resolve().parents[2]
ATLAS_DIR = BASE_DIR / "atlas"
DIST_DIR = ATLAS_DIR / "dist"
ASSETS_DIR = DIST_DIR / "assets"
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env", override=True)

from storage.database import (
    init_db, get_all_leads, get_unsynced_leads, mark_leads_synced,
    create_job, get_job, get_all_jobs, update_job, init_jobs_table
)
from integrations.klaviyo import sync_leads_to_klaviyo
import main as scraper_main

app = FastAPI(title="Piranha Atlas API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()
init_jobs_table()

# In-memory SSE queue per job
_job_queues: dict[str, asyncio.Queue] = {}


# ── Models ──────────────────────────────────────────────────────────────────

class JobStartRequest(BaseModel):
    query: str = "estudio de tatuaje"
    cities: list[str] = []
    enrich_email: bool = True
    use_firecrawl: bool = False
    validate_and_enrich: bool = False
    auto_klaviyo: bool = False


# ── Leads ────────────────────────────────────────────────────────────────────

@app.get("/api/leads")
def list_leads():
    return get_all_leads()


# ── Validation (deve vir ANTES de /api/leads/{lead_id}) ──────────────────────

class ValidateRequest(BaseModel):
    ids: list[int]
    auto_klaviyo: bool = True


_validation_queues: dict[str, asyncio.Queue] = {}
_enrichment_queues: dict[str, asyncio.Queue] = {}


@app.post("/api/leads/validate")
async def start_validation(req: ValidateRequest):
    val_id = str(uuid.uuid4())[:8]
    _validation_queues[val_id] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_validation():
        from validators.contact_validator import validate_lead_contacts
        from storage.database import get_connection

        leads = get_all_leads()
        targets = [l for l in leads if l["id"] in req.ids]
        total = len(targets)
        changed = 0
        cleared_website = cleared_email = cleared_phone = 0

        for i, lead in enumerate(targets, 1):
            result = validate_lead_contacts(lead)
            clean = result["clean"]

            w_changed = clean["website"] != lead.get("website")
            e_changed  = clean["email"]   != lead.get("email")
            p_changed  = clean["phone"]   != lead.get("phone")
            any_changed = w_changed or e_changed or p_changed

            if any_changed:
                changed += 1
                if w_changed: cleared_website += 1
                if e_changed: cleared_email  += 1
                if p_changed: cleared_phone  += 1

                instagram_url = lead.get("instagram_url")
                facebook_url = lead.get("facebook_url")
                if w_changed and lead.get("website") and not clean["website"]:
                    try:
                        host = urlparse(lead["website"]).netloc.lower().lstrip("www.")
                    except Exception:
                        host = ""
                    if host == "instagram.com" and not instagram_url:
                        instagram_url = lead["website"]
                    if host == "facebook.com" and not facebook_url:
                        facebook_url = lead["website"]

                with get_connection() as conn:
                    conn.execute(
                        """
                        UPDATE leads
                        SET website=?, email=?, phone=?, instagram_url=?, facebook_url=?,
                            validated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                        """,
                        (clean["website"], clean["email"], clean["phone"], instagram_url, facebook_url, lead["id"])
                    )
                    conn.commit()
            else:
                # marca como validado mesmo sem alterações
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE leads SET validated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (lead["id"],)
                    )
                    conn.commit()

            event = {
                "type": "lead_check",
                "id": lead["id"],
                "name": lead.get("name", ""),
                "index": i,
                "total": total,
                "changed": any_changed,
                "website_cleared": w_changed,
                "email_cleared": e_changed,
                "phone_cleared": p_changed,
            }
            loop.call_soon_threadsafe(_validation_queues[val_id].put_nowait, event)

        # Klaviyo sync automático após validação
        klaviyo_synced = 0
        if req.auto_klaviyo:
            try:
                list_id = os.getenv("KLAVIYO_LIST_ID", "S9Qa55")
                unsynced = get_unsynced_leads()
                if unsynced:
                    sync_result = sync_leads_to_klaviyo(unsynced, list_id)
                    klaviyo_synced = sync_result.get("synced", 0)
                    if klaviyo_synced > 0:
                        mark_leads_synced([l["id"] for l in unsynced])
            except Exception:
                pass

        done_event = {
            "type": "validation_complete",
            "total": total,
            "changed": changed,
            "cleared_website": cleared_website,
            "cleared_email": cleared_email,
            "cleared_phone": cleared_phone,
            "klaviyo_synced": klaviyo_synced,
        }
        loop.call_soon_threadsafe(_validation_queues[val_id].put_nowait, done_event)
        loop.call_soon_threadsafe(_validation_queues[val_id].put_nowait, {"type": "__done__"})

    import threading
    threading.Thread(target=run_validation, daemon=True).start()
    return {"validation_id": val_id}


@app.get("/api/leads/validate/{val_id}/stream")
async def stream_validation(val_id: str):
    if val_id not in _validation_queues:
        raise HTTPException(404, "Validation not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = _validation_queues[val_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
                continue
            if event.get("type") == "__done__":
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/leads/enrich")
async def start_enrichment(req: ValidateRequest):
    enrich_id = str(uuid.uuid4())[:8]
    _enrichment_queues[enrich_id] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_enrichment():
        from storage.database import get_connection

        leads = get_all_leads()
        targets = [l for l in leads if l["id"] in req.ids]
        total = len(targets)
        changed = 0
        found_website = found_email = found_phone = found_social = 0

        for i, lead in enumerate(targets, 1):
            original = {
                "website": lead.get("website"),
                "email": lead.get("email"),
                "phone": lead.get("phone"),
                "instagram_url": lead.get("instagram_url"),
                "facebook_url": lead.get("facebook_url"),
            }

            scraper_main._validate_and_enrich_studio(lead, enrich_email=True)

            w_found = not original["website"] and bool(lead.get("website"))
            e_found = not original["email"] and bool(lead.get("email"))
            p_found = not original["phone"] and bool(lead.get("phone"))
            social_found = (
                (not original["instagram_url"] and bool(lead.get("instagram_url"))) or
                (not original["facebook_url"] and bool(lead.get("facebook_url")))
            )
            any_changed = any(
                lead.get(field) != original[field]
                for field in original
            )

            if any_changed:
                changed += 1
                if w_found:
                    found_website += 1
                if e_found:
                    found_email += 1
                if p_found:
                    found_phone += 1
                if social_found:
                    found_social += 1

            with get_connection() as conn:
                conn.execute(
                    """
                    UPDATE leads
                    SET website=?, email=?, phone=?, instagram_url=?, facebook_url=?,
                        validated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        lead.get("website"),
                        lead.get("email"),
                        lead.get("phone"),
                        lead.get("instagram_url"),
                        lead.get("facebook_url"),
                        lead["id"],
                    )
                )
                conn.commit()

            details: list[str] = []
            if w_found:
                details.append("website encontrado")
            if e_found:
                details.append("email encontrado")
            if p_found:
                details.append("telefone encontrado")
            if social_found:
                details.append("social encontrado")

            event = {
                "type": "lead_enrich",
                "id": lead["id"],
                "name": lead.get("name", ""),
                "index": i,
                "total": total,
                "changed": any_changed,
                "website_found": w_found,
                "email_found": e_found,
                "phone_found": p_found,
                "social_found": social_found,
                "details": ", ".join(details),
            }
            loop.call_soon_threadsafe(_enrichment_queues[enrich_id].put_nowait, event)

        done_event = {
            "type": "enrichment_complete",
            "total": total,
            "changed": changed,
            "found_website": found_website,
            "found_email": found_email,
            "found_phone": found_phone,
            "found_social": found_social,
        }
        loop.call_soon_threadsafe(_enrichment_queues[enrich_id].put_nowait, done_event)
        loop.call_soon_threadsafe(_enrichment_queues[enrich_id].put_nowait, {"type": "__done__"})

    import threading
    threading.Thread(target=run_enrichment, daemon=True).start()
    return {"enrichment_id": enrich_id}


@app.get("/api/leads/enrich/{enrich_id}/stream")
async def stream_enrichment(enrich_id: str):
    if enrich_id not in _enrichment_queues:
        raise HTTPException(404, "Enrichment not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = _enrichment_queues[enrich_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
                continue
            if event.get("type") == "__done__":
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Lead by ID (DEPOIS das rotas estáticas de /api/leads/*) ──────────────────

class DeleteLeadsRequest(BaseModel):
    ids: list[int]


@app.delete("/api/leads")
def delete_leads(req: DeleteLeadsRequest):
    if not req.ids:
        return {"deleted": 0}
    from storage.database import get_connection
    with get_connection() as conn:
        placeholders = ",".join("?" * len(req.ids))
        conn.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", req.ids)
        conn.commit()
    return {"deleted": len(req.ids)}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int):
    leads = get_all_leads()
    lead = next((l for l in leads if l["id"] == lead_id), None)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


# ── Jobs ─────────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    return get_all_jobs()


@app.get("/api/jobs/{job_id}")
def get_job_endpoint(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/jobs/start")
async def start_job(req: JobStartRequest):
    from config import SPAIN_CITIES
    job_id = str(uuid.uuid4())[:8]
    cities = req.cities if req.cities else SPAIN_CITIES
    create_job(job_id, req.query, cities)
    _job_queues[job_id] = asyncio.Queue()

    loop = asyncio.get_event_loop()

    def callback(event_type: str, data: dict):
        data["type"] = event_type
        loop.call_soon_threadsafe(_job_queues[job_id].put_nowait, data)

        if event_type == "city_progress":
            update_job(job_id,
                leads_found=data.get("leads_found", 0),
                leads_with_email=data.get("leads_with_email", 0))

        if event_type == "job_complete":
            finished = datetime.utcnow().isoformat()
            job = get_job(job_id)
            started = datetime.fromisoformat(job["started_at"])
            duration = (datetime.utcnow() - started).total_seconds()
            update_job(job_id,
                status="completed",
                finished_at=finished,
                duration_seconds=duration,
                leads_found=data.get("total_leads", 0),
                klaviyo_synced=data.get("klaviyo_synced", 0))
            loop.call_soon_threadsafe(_job_queues[job_id].put_nowait, {"type": "__done__"})

    def run_scraper():
        try:
            scraper_main.run(
                progress_callback=callback,
                cities_override=cities,
                query_override=req.query,
                enrich_email=req.enrich_email,
                use_firecrawl=req.use_firecrawl,
                auto_klaviyo=req.auto_klaviyo,
                validate_and_enrich=req.validate_and_enrich,
            )
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
            loop.call_soon_threadsafe(_job_queues[job_id].put_nowait, {"type": "__done__", "error": str(e)})

    import threading
    threading.Thread(target=run_scraper, daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    if job_id not in _job_queues:
        raise HTTPException(404, "Job not found or not running")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = _job_queues[job_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
                continue
            if event.get("type") == "__done__":
                yield f"data: {json.dumps(event)}\n\n"
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Klaviyo ──────────────────────────────────────────────────────────────────

@app.delete("/api/klaviyo/list")
def klaviyo_clear_list():
    """Remove all profiles from the Klaviyo list (does not delete profiles)."""
    import requests as req_lib
    klaviyo_key = os.getenv("KLAVIYO_PRIVATE_API_KEY")
    list_id = os.getenv("KLAVIYO_LIST_ID", "S9Qa55")
    if not klaviyo_key:
        raise HTTPException(400, "KLAVIYO_PRIVATE_API_KEY não definida")

    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "revision": "2024-10-15",
        "Content-Type": "application/json",
    }

    removed = 0
    cursor = None
    while True:
        params = {"page[cursor]": cursor} if cursor else {}
        r = req_lib.get(
            f"https://a.klaviyo.com/api/lists/{list_id}/relationships/profiles/",
            headers=headers, params=params, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        profiles = data.get("data", [])
        if not profiles:
            break

        # Remove this batch from the list
        req_lib.delete(
            f"https://a.klaviyo.com/api/lists/{list_id}/relationships/profiles/",
            headers=headers,
            json={"data": profiles},
            timeout=15
        )
        removed += len(profiles)

        cursor = data.get("links", {}).get("next")
        if not cursor:
            break

    # Reset klaviyo_synced flags in DB
    with get_connection() as conn:
        conn.execute("UPDATE leads SET klaviyo_synced = 0")
        conn.commit()

    return {"removed": removed, "list_id": list_id}


@app.post("/api/klaviyo/sync")
def klaviyo_sync():
    list_id = os.getenv("KLAVIYO_LIST_ID", "S9Qa55")
    unsynced = get_unsynced_leads()
    if not unsynced:
        return {"synced": 0, "skipped": 0, "message": "No pending leads"}
    result = sync_leads_to_klaviyo(unsynced, list_id)
    if result["synced"] > 0:
        mark_leads_synced([l["id"] for l in unsynced])
    return result


# ── Email Search ─────────────────────────────────────────────────────────────

_email_search_queues: dict[str, asyncio.Queue] = {}


@app.post("/api/leads/search-emails")
async def start_email_search():
    search_id = str(uuid.uuid4())[:8]
    _email_search_queues[search_id] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def run_search():
        from collectors.google_search_extractor import search_email_for_lead
        leads = get_all_leads()
        targets = [l for l in leads if not l.get("email")]
        total = len(targets)
        found = 0

        for i, lead in enumerate(targets, 1):
            name = (lead.get("name") or "").strip()
            city = (lead.get("city") or "").strip() or "Spain"
            if not name:
                continue

            email = None
            try:
                email = search_email_for_lead(name, city)
            except Exception:
                pass

            if email:
                with get_connection() as conn:
                    conn.execute("UPDATE leads SET email = ? WHERE id = ?", (email, lead["id"]))
                    conn.commit()
                found += 1

            event = {
                "type": "email_search_progress",
                "index": i,
                "total": total,
                "lead_id": lead["id"],
                "name": name,
                "email": email,
                "found_so_far": found,
            }
            loop.call_soon_threadsafe(_email_search_queues[search_id].put_nowait, event)

        done = {"type": "email_search_complete", "total": total, "found": found}
        loop.call_soon_threadsafe(_email_search_queues[search_id].put_nowait, done)
        loop.call_soon_threadsafe(_email_search_queues[search_id].put_nowait, {"type": "__done__"})

    import threading
    threading.Thread(target=run_search, daemon=True).start()
    return {"search_id": search_id}


@app.get("/api/leads/search-emails/{search_id}/stream")
async def stream_email_search(search_id: str):
    if search_id not in _email_search_queues:
        raise HTTPException(404, "Search not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = _email_search_queues[search_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
                continue
            if event.get("type") == "__done__":
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Status ───────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    import requests as req_lib
    firecrawl_url = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
    firecrawl_ok = False
    try:
        r = req_lib.get(f"{firecrawl_url}/health", timeout=2)
        firecrawl_ok = r.status_code == 200
    except Exception:
        pass

    google_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    klaviyo_key = os.getenv("KLAVIYO_PRIVATE_API_KEY", "")

    serper_key = os.getenv("SERPER_API_KEY", "")

    return {
        "google_places": {"configured": bool(google_key), "key_preview": google_key[:8] + "..." if google_key else ""},
        "klaviyo": {"configured": bool(klaviyo_key), "list_id": os.getenv("KLAVIYO_LIST_ID", "S9Qa55")},
        "firecrawl": {"online": firecrawl_ok, "url": firecrawl_url},
        "serper": {"configured": bool(serper_key), "key_preview": serper_key[:8] + "..." if serper_key else ""},
    }


# ── Frontend SPA ─────────────────────────────────────────────────────────────

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="atlas-assets")


@app.get("/", include_in_schema=False)
async def atlas_index():
    index_file = DIST_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(503, "Atlas frontend build not found")
    return FileResponse(index_file)


@app.get("/{full_path:path}", include_in_schema=False)
async def atlas_spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404, "Not found")

    target = DIST_DIR / full_path
    if full_path and target.is_file():
        return FileResponse(target)

    index_file = DIST_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(503, "Atlas frontend build not found")
    return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("atlas.api.server:app", host="0.0.0.0", port=8000)
