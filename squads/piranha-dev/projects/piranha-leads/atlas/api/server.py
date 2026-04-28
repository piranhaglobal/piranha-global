import asyncio
import base64
import hashlib
import hmac
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
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
    init_db, get_all_leads, get_leads_for_job, get_unsynced_leads, mark_leads_synced,
    create_job, get_job, get_all_jobs, update_job, init_jobs_table, get_connection
)
from storage.research_chat import (
    init_research_chat_tables, create_thread, get_thread, list_threads, add_message,
    list_messages, get_context, upsert_context, create_brief, update_brief,
    find_research_log_by_key, create_research_log, list_research_log, list_complete_contexts,
    make_dedupe_key, list_folders, create_folder, set_thread_folder, delete_thread,
    clear_context, delete_folder, update_thread_title, set_thread_cron_enabled,
    list_queued_contexts,
)
from storage.klaviyo_lists import load_klaviyo_lists, upsert_klaviyo_list, delete_klaviyo_list
from integrations.klaviyo import get_list_details, sync_leads_to_klaviyo
from integrations.openai_chat import chat_response, transcribe_audio
from utils.places_research import build_places_market_snapshot, should_use_places_intelligence
from utils.research_context import context_to_brief_text, merge_context
import main as scraper_main

app = FastAPI(title="Piranha Atlas API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

init_db()
init_jobs_table()
init_research_chat_tables()

# In-memory SSE queue per job
_job_queues: dict[str, asyncio.Queue] = {}


def _auth_domain() -> str:
    return os.getenv("ATLAS_AUTH_DOMAIN", "piranha.com.pt").strip().lower()


def _auth_required(request: Request | None = None) -> bool:
    configured = os.getenv("ATLAS_REQUIRE_AUTH")
    if configured is not None:
        return configured == "1"

    # Safe default: local development can run without auth, public domains cannot.
    host = (request.url.hostname if request else "") or ""
    return host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _google_oauth_configured() -> bool:
    return bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID") and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"))


def _auth_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(f"/?auth_error={quote(message)}", status_code=303)


def _cookie_secret() -> bytes:
    return os.getenv("ATLAS_SESSION_SECRET", os.getenv("OPENAI_API_KEY", "dev-secret")).encode("utf-8")


def _sign_payload(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    sig = hmac.new(_cookie_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _read_session(request: Request) -> dict | None:
    raw = request.cookies.get("atlas_session")
    if not raw or "." not in raw:
        return None
    body, sig = raw.rsplit(".", 1)
    expected = hmac.new(_cookie_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(body.encode("utf-8")))
    except Exception:
        return None


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not _auth_required(request):
        return await call_next(request)

    path = request.url.path
    if path.startswith("/api/auth") or path.startswith("/assets"):
        return await call_next(request)
    if path.startswith("/api/") and not _read_session(request):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


# ── Models ──────────────────────────────────────────────────────────────────

class JobStartRequest(BaseModel):
    query: str = "estudio de tatuaje"
    cities: list[str] = []
    enrich_email: bool = True
    use_firecrawl: bool = False
    validate_and_enrich: bool = False
    auto_klaviyo: bool = False


class ChatThreadCreateRequest(BaseModel):
    title: str = "Nova pesquisa"
    folder_id: str | None = None


class ChatMessageRequest(BaseModel):
    content: str


class ChatFolderCreateRequest(BaseModel):
    name: str


class ChatThreadFolderRequest(BaseModel):
    folder_id: str | None = None


class ChatContextUpdateRequest(BaseModel):
    category: str | None = None
    region: str | None = None
    cities: list[str] = []
    leads_per_city: int | None = None
    min_reviews: int | None = None
    query: str | None = None
    objective: str | None = None


class ChatPlacesInsightsRequest(BaseModel):
    prompt: str | None = None


class ChatThreadRenameRequest(BaseModel):
    title: str


class ChatThreadQueueRequest(BaseModel):
    enabled: bool


# ── Auth ─────────────────────────────────────────────────────────────────────

@app.get("/api/auth/me")
def auth_me(request: Request):
    if not _auth_required(request):
        return {"authenticated": True, "user": {"email": "dev@piranha.com.pt", "name": "Dev"}}
    session = _read_session(request)
    if not session:
        raise HTTPException(401, "Authentication required")
    return {"authenticated": True, "user": session}


@app.get("/api/auth/config")
def auth_config(request: Request):
    return {
        "required": _auth_required(request),
        "google_configured": _google_oauth_configured(),
        "domain": _auth_domain(),
    }


@app.get("/api/auth/google/login")
def google_login(request: Request):
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id or not os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"):
        return _auth_error_redirect("Google OAuth não configurado no servidor")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or str(request.url_for("google_callback"))
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "hd": _auth_domain(),
        "prompt": "select_account",
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@app.get("/api/auth/google/callback")
def google_callback(request: Request, code: str | None = None, error: str | None = None):
    import requests as req_lib

    if error:
        return _auth_error_redirect("Login Google cancelado ou recusado")
    if not code:
        return _auth_error_redirect("Código de login Google ausente")

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        return _auth_error_redirect("Google OAuth não configurado no servidor")

    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or str(request.url_for("google_callback"))
    try:
        token_res = req_lib.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        token_res.raise_for_status()
        token = token_res.json()["access_token"]
        user_res = req_lib.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        user_res.raise_for_status()
    except Exception:
        return _auth_error_redirect("Não foi possível conectar a conta Google")

    user = user_res.json()
    email = (user.get("email") or "").lower()
    if not email.endswith(f"@{_auth_domain()}"):
        return _auth_error_redirect(f"Acesso restrito a contas @{_auth_domain()}")

    response = RedirectResponse("/")
    response.set_cookie(
        "atlas_session",
        _sign_payload({"email": email, "name": user.get("name") or email}),
        httponly=True,
        secure=os.getenv("ATLAS_COOKIE_SECURE", "1") == "1",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.post("/api/auth/logout")
def auth_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("atlas_session")
    return response


def _launch_scraper_job(req: JobStartRequest) -> str:
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
                job_id=job_id,
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
    return job_id


def _fallback_chat_reply(context: dict) -> str:
    missing_fields = context.get("missing_fields") or []
    if isinstance(missing_fields, str):
        missing_fields = [field for field in missing_fields.split(",") if field]

    if missing_fields:
        labels = {
            "category": "categoria",
            "region_or_cities": "região ou cidades",
            "leads_per_city": "leads por cidade",
            "min_reviews": "mínimo de reviews",
        }
        missing = ", ".join(labels.get(field, field) for field in missing_fields)
        return f"Tenho parte do briefing. Falta definir: {missing}."
    return "Contexto completo. Vou preparar o briefing e criar o job de scraping com estes parâmetros."


def _format_places_snapshot(snapshot: dict | None) -> str:
    if not snapshot:
        return ""
    if not snapshot.get("available"):
        return f"Google Places indisponível: {snapshot.get('reason')}"

    lines = [
        snapshot.get("summary", "").strip(),
        f"País/região: {snapshot.get('country')}",
        f"Query: {snapshot.get('query')}",
        f"Reviews mínimas: {snapshot.get('min_reviews')}",
    ]
    for row in (snapshot.get("top_cities") or [])[:5]:
        if row.get("error"):
            lines.append(f"- {row.get('city')}: erro ({row.get('error')})")
            continue
        lines.append(
            f"- {row.get('city')}: {row.get('qualified_count', 0)} leads, melhor com {row.get('best_reviews', 0)} reviews"
        )
        for business in row.get("best_businesses") or []:
            lines.append(f"  • {business.get('name')} ({business.get('reviews', 0)} reviews)")
    return "\n".join(lines)


def _chat_completion_for_thread(thread_id: str, context: dict, places_snapshot: dict | None = None) -> tuple[str, str | None]:
    messages = list_messages(thread_id)[-12:]
    system = {
        "role": "system",
        "content": (
            "És o Research Chat do Atlas, responsável por transformar conversas em briefings "
            "operacionais de scraping de leads. Responde em português, de forma curta e operacional. "
            "Nunca inventes filtros obrigatórios. Se faltar categoria, região/cidades, leads por cidade "
            "ou reviews mínimas, pede só o que falta. Quando houver snapshot do Google Places, usa-o "
            "para recomendar cidades e hipóteses reais de pesquisa. Contexto estruturado atual:\n"
            f"{context_to_brief_text(context)}"
            + (f"\n\nSnapshot Google Places:\n{_format_places_snapshot(places_snapshot)}" if places_snapshot else "")
        ),
    }
    openai_messages = [system] + [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
        if msg["role"] in {"user", "assistant"}
    ]
    model = (
        os.getenv("OPENAI_PLANNER_MODEL", "gpt-5.5")
        if not context.get("missing_fields")
        else os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )
    try:
        return chat_response(openai_messages, model=model), model
    except Exception:
        return _fallback_chat_reply(context), None


def _execute_complete_context(thread_id: str, context: dict) -> dict | None:
    if context.get("missing_fields"):
        return None

    brief = create_brief(thread_id, context)
    dedupe_key = brief["payload"]["dedupe_key"]
    existing = find_research_log_by_key(dedupe_key)
    if existing:
        update_brief(brief["id"], status="blocked_duplicate")
        return {"brief": brief, "blocked_duplicate": True, "existing_log": existing}

    job_id = _launch_scraper_job(JobStartRequest(
        query=context["query"],
        cities=context["cities"],
        enrich_email=True,
        use_firecrawl=False,
        validate_and_enrich=False,
        auto_klaviyo=False,
    ))
    update_brief(brief["id"], status="executed", executed_job_id=job_id)
    log = create_research_log(thread_id, brief["id"], context, job_id, "executed")
    return {"brief": brief, "job_id": job_id, "research_log": log, "blocked_duplicate": False}


def _seconds_until_next_daily_run() -> float:
    tz = ZoneInfo("Europe/Lisbon")
    now = datetime.now(tz)
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()


def _next_daily_run_at() -> datetime:
    tz = ZoneInfo("Europe/Lisbon")
    now = datetime.now(tz)
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return target


def _run_daily_chat_context() -> dict | None:
    for context in list_complete_contexts():
        if find_research_log_by_key(make_dedupe_key(context)):
            continue
        return _execute_complete_context(context["thread_id"], context)
    return None


async def _daily_research_scheduler() -> None:
    while True:
        await asyncio.sleep(_seconds_until_next_daily_run())
        try:
            _run_daily_chat_context()
        except Exception as e:
            print(f"[daily-research-chat] erro: {e}")


@app.on_event("startup")
async def start_daily_research_scheduler():
    if os.getenv("ATLAS_DAILY_CHAT_CRON", "1") == "1":
        asyncio.create_task(_daily_research_scheduler())


# ── Research Chat ────────────────────────────────────────────────────────────

@app.get("/api/chat/threads")
def chat_threads():
    return list_threads()


@app.post("/api/chat/threads")
def chat_create_thread(req: ChatThreadCreateRequest):
    return create_thread(req.title, req.folder_id)


@app.delete("/api/chat/threads/{thread_id}")
def chat_delete_thread(thread_id: str):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    delete_thread(thread_id)
    return {"deleted": thread_id}


@app.post("/api/chat/threads/{thread_id}/folder")
def chat_move_thread(thread_id: str, req: ChatThreadFolderRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    set_thread_folder(thread_id, req.folder_id)
    return get_thread(thread_id)


@app.get("/api/chat/folders")
def chat_folders():
    return list_folders()


@app.post("/api/chat/folders")
def chat_create_folder(req: ChatFolderCreateRequest):
    return create_folder(req.name)


@app.delete("/api/chat/folders/{folder_id}")
def chat_delete_folder(folder_id: str):
    try:
        delete_folder(folder_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"deleted": folder_id}


@app.post("/api/chat/threads/{thread_id}/rename")
def chat_rename_thread(thread_id: str, req: ChatThreadRenameRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    update_thread_title(thread_id, req.title.strip())
    return get_thread(thread_id)


@app.post("/api/chat/threads/{thread_id}/queue")
def chat_set_thread_queue(thread_id: str, req: ChatThreadQueueRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    set_thread_cron_enabled(thread_id, req.enabled)
    return get_thread(thread_id)


@app.get("/api/chat/queue")
def chat_queue():
    next_run = _next_daily_run_at()
    seconds_until = int(max(_seconds_until_next_daily_run(), 0))
    items = []
    for item in list_queued_contexts():
        queued = bool(item.get("usable_for_cron"))
        dedupe_exists = bool(find_research_log_by_key(make_dedupe_key(item)))
        status = "scheduled" if queued and not dedupe_exists else "paused" if not queued else "already_done"
        items.append({
            **item,
            "queue_status": status,
            "scheduled_for": next_run.isoformat(),
            "seconds_until_run": seconds_until,
        })
    return {"scheduled_for": next_run.isoformat(), "seconds_until_run": seconds_until, "items": items}


@app.get("/api/chat/threads/{thread_id}/messages")
def chat_thread_messages(thread_id: str):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    return {"messages": list_messages(thread_id), "context": get_context(thread_id)}


@app.post("/api/chat/threads/{thread_id}/messages")
async def chat_send_message(thread_id: str, req: ChatMessageRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")

    user_content = req.content.strip()
    if not user_content:
        raise HTTPException(400, "Message content is required")

    add_message(thread_id, "user", user_content)
    existing_context = get_context(thread_id)
    context = upsert_context(thread_id, merge_context(existing_context, user_content))
    places_snapshot = build_places_market_snapshot(context, user_content) if should_use_places_intelligence(user_content, context) else None
    reply, model = _chat_completion_for_thread(thread_id, context, places_snapshot=places_snapshot)
    assistant_message = add_message(thread_id, "assistant", reply, model=model)
    execution = _execute_complete_context(thread_id, context)

    return {
        "message": assistant_message,
        "context": context,
        "context_complete": context["completeness_status"] == "complete",
        "can_execute_scrape": context["completeness_status"] == "complete",
        "execution": execution,
        "places_snapshot": places_snapshot,
    }


@app.post("/api/chat/threads/{thread_id}/audio")
async def chat_audio_message(thread_id: str, file: UploadFile = File(...)):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")

    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(400, "Audio file required")

    audio_dir = BASE_DIR / "data" / "chat-audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    audio_path = audio_dir / f"{thread_id}-{uuid.uuid4().hex[:10]}{suffix}"
    with audio_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        transcript = transcribe_audio(audio_path)
    except Exception as e:
        raise HTTPException(502, f"Audio transcription failed: {e}")

    user_msg = add_message(
        thread_id,
        "user",
        transcript,
        model=os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
        audio_path=str(audio_path),
        transcript=transcript,
    )
    existing_context = get_context(thread_id)
    context = upsert_context(thread_id, merge_context(existing_context, transcript))
    reply, model = _chat_completion_for_thread(thread_id, context)
    assistant_message = add_message(thread_id, "assistant", reply, model=model)
    execution = _execute_complete_context(thread_id, context)

    return {
        "transcript": transcript,
        "user_message": user_msg,
        "message": assistant_message,
        "context": context,
        "context_complete": context["completeness_status"] == "complete",
        "can_execute_scrape": context["completeness_status"] == "complete",
        "execution": execution,
    }


@app.post("/api/chat/threads/{thread_id}/transcribe")
async def chat_transcribe_audio(thread_id: str, file: UploadFile = File(...)):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")

    if file.content_type and not file.content_type.startswith("audio/"):
        raise HTTPException(400, "Audio file required")

    audio_dir = BASE_DIR / "data" / "chat-audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    audio_path = audio_dir / f"draft-{thread_id}-{uuid.uuid4().hex[:10]}{suffix}"
    with audio_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        transcript = transcribe_audio(audio_path)
    except Exception as e:
        raise HTTPException(502, f"Audio transcription failed: {e}")
    return {"transcript": transcript}


@app.post("/api/chat/threads/{thread_id}/places-insights")
def chat_places_insights(thread_id: str, req: ChatPlacesInsightsRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    context = get_context(thread_id) or {}
    snapshot = build_places_market_snapshot(context, req.prompt)
    return {"snapshot": snapshot}


@app.put("/api/chat/threads/{thread_id}/context")
def chat_update_context(thread_id: str, req: ChatContextUpdateRequest):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    context = {
        "category": req.category.strip() if req.category else None,
        "region": req.region.strip() if req.region else None,
        "cities": req.cities,
        "leads_per_city": req.leads_per_city,
        "min_reviews": req.min_reviews,
        "query": req.query.strip() if req.query else None,
        "objective": req.objective.strip() if req.objective else None,
        "missing_fields": [],
    }
    if not context["category"]:
        context["missing_fields"].append("category")
    if not context["cities"] and not context["region"]:
        context["missing_fields"].append("region_or_cities")
    if not context["leads_per_city"]:
        context["missing_fields"].append("leads_per_city")
    if not context["min_reviews"]:
        context["missing_fields"].append("min_reviews")
    return upsert_context(thread_id, context)


@app.delete("/api/chat/threads/{thread_id}/context")
def chat_clear_context(thread_id: str):
    if not get_thread(thread_id):
        raise HTTPException(404, "Thread not found")
    clear_context(thread_id)
    return {"cleared": thread_id}


@app.get("/api/research/log")
def research_log():
    return list_research_log()


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


class KlaviyoListRequest(BaseModel):
    list_id: str


class KlaviyoSyncSelectedRequest(BaseModel):
    ids: list[int]
    list_id: str


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


@app.get("/api/jobs/{job_id}/leads")
def get_job_leads_endpoint(job_id: str):
    return get_leads_for_job(job_id)


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
    job_id = _launch_scraper_job(req)
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


@app.get("/api/klaviyo/lists")
def klaviyo_lists():
    configured = load_klaviyo_lists()
    default_list_id = os.getenv("KLAVIYO_LIST_ID", "S9Qa55")
    if default_list_id and not any(item["id"] == default_list_id for item in configured):
        try:
            configured = upsert_klaviyo_list({
                **get_list_details(default_list_id),
                "source": "env",
            })
        except Exception:
            pass
    return {"lists": configured, "default_list_id": default_list_id}


@app.post("/api/klaviyo/lists")
def klaviyo_add_list(req: KlaviyoListRequest):
    details = get_list_details(req.list_id.strip())
    lists = upsert_klaviyo_list({
        **details,
        "source": "manual",
    })
    return {"lists": lists, "added": details}


@app.delete("/api/klaviyo/lists/{list_id}")
def klaviyo_remove_list(list_id: str):
    lists = delete_klaviyo_list(list_id)
    return {"lists": lists, "removed": list_id}


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


@app.post("/api/klaviyo/sync-selected")
def klaviyo_sync_selected(req: KlaviyoSyncSelectedRequest):
    if not req.ids:
        return {"synced": 0, "skipped": 0, "jobs": []}
    leads = [lead for lead in get_all_leads() if lead["id"] in req.ids]
    result = sync_leads_to_klaviyo(leads, req.list_id)
    if result["synced"] > 0:
        synced_ids = [lead["id"] for lead in leads if lead.get("email") or lead.get("phone")]
        mark_leads_synced(synced_ids)
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
        "klaviyo": {
            "configured": bool(klaviyo_key),
            "list_id": os.getenv("KLAVIYO_LIST_ID", "S9Qa55"),
            "lists": load_klaviyo_lists(),
        },
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
