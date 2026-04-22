import os
import time
import requests
from datetime import datetime

KLAVIYO_API_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-10-15"
BATCH_SIZE = 100  # profiles per bulk import job


def _headers() -> dict:
    api_key = os.getenv("KLAVIYO_PRIVATE_API_KEY")
    if not api_key:
        raise EnvironmentError("KLAVIYO_PRIVATE_API_KEY não definida no .env")
    return {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": KLAVIYO_REVISION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _build_profile_payload(lead: dict) -> dict:
    attrs = {}

    if lead.get("email"):
        attrs["email"] = lead["email"]
    if lead.get("phone"):
        phone = lead["phone"]
        if not phone.startswith("+"):
            phone = "+34" + phone.lstrip("0")
        attrs["phone_number"] = phone
    if lead.get("name"):
        attrs["first_name"] = lead["name"]

    location = {}
    if lead.get("city"):
        location["city"] = lead["city"]
    if lead.get("address"):
        location["address1"] = lead["address"]
    if location:
        attrs["location"] = location

    props = {}
    if lead.get("rating") is not None:
        props["rating"] = lead["rating"]
    if lead.get("total_reviews") is not None:
        props["total_reviews"] = lead["total_reviews"]
    if lead.get("website"):
        props["website"] = lead["website"]
    if lead.get("business_status"):
        props["business_status"] = lead["business_status"]
    if lead.get("source"):
        props["source"] = lead["source"]
    if lead.get("created_at"):
        props["scraped_at"] = lead["created_at"]
    if props:
        attrs["properties"] = props

    return {"type": "profile", "attributes": attrs}


def _submit_bulk_import(profiles: list[dict], list_id: str) -> str:
    payload = {
        "data": {
            "type": "profile-bulk-import-job",
            "attributes": {
                "profiles": {"data": profiles}
            },
            "relationships": {
                "lists": {
                    "data": [{"type": "list", "id": list_id}]
                }
            },
        }
    }
    resp = requests.post(
        f"{KLAVIYO_API_BASE}/profile-bulk-import-jobs/",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def _wait_for_job(job_id: str, max_wait: int = 120) -> str:
    elapsed = 0
    while elapsed < max_wait:
        resp = requests.get(
            f"{KLAVIYO_API_BASE}/profile-bulk-import-jobs/{job_id}/",
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json()["data"]["attributes"]["status"]
        if status in ("complete", "cancelled"):
            return status
        time.sleep(5)
        elapsed += 5
    return "timeout"


def get_list_details(list_id: str) -> dict:
    resp = requests.get(
        f"{KLAVIYO_API_BASE}/lists/{list_id}/",
        headers=_headers(),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    attrs = data.get("attributes", {})
    return {
        "id": data["id"],
        "name": attrs.get("name") or data["id"],
        "created": attrs.get("created"),
        "updated": attrs.get("updated"),
    }


def sync_leads_to_klaviyo(leads: list[dict], list_id: str) -> dict:
    """
    Syncs a list of leads to a Klaviyo list via bulk import.
    Returns a summary dict with counts.
    """
    # Only sync leads that have email or phone
    eligible = [l for l in leads if l.get("email") or l.get("phone")]
    skipped = len(leads) - len(eligible)

    if not eligible:
        print("  Klaviyo: nenhum lead com email ou telefone para sincronizar.")
        return {"synced": 0, "skipped": skipped, "jobs": []}

    jobs = []
    for i in range(0, len(eligible), BATCH_SIZE):
        batch = eligible[i : i + BATCH_SIZE]
        profiles = [_build_profile_payload(l) for l in batch]

        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(eligible) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Klaviyo: enviando lote {batch_num}/{total_batches} ({len(batch)} profiles)...")

        job_id = _submit_bulk_import(profiles, list_id)
        status = _wait_for_job(job_id)
        jobs.append({"job_id": job_id, "size": len(batch), "status": status})
        print(f"  Klaviyo: job {job_id} → {status}")

    synced = sum(j["size"] for j in jobs if j["status"] == "complete")
    return {"synced": synced, "skipped": skipped, "jobs": jobs}
