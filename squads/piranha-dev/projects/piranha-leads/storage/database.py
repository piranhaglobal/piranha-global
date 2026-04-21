import csv
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "leads.db"
CSV_PATH = Path(__file__).parent.parent / "data" / "leads.csv"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id      TEXT UNIQUE,
    name          TEXT,
    city          TEXT,
    address       TEXT,
    phone         TEXT,
    website       TEXT,
    email         TEXT,
    rating        REAL,
    total_reviews INTEGER,
    business_status TEXT,
    source        TEXT DEFAULT 'google_places',
    status        TEXT DEFAULT 'new',
    klaviyo_synced INTEGER DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATE_SQL = """
ALTER TABLE leads ADD COLUMN klaviyo_synced INTEGER DEFAULT 0;
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        # migrate existing DBs that don't have klaviyo_synced column
        try:
            conn.execute(MIGRATE_SQL)
        except sqlite3.OperationalError:
            pass
        conn.commit()
    init_jobs_table()


def upsert_lead(lead: dict):
    """
    Inserts a new lead or updates if place_id already exists.
    Existing emails/phones are preserved if new data is empty.
    """
    sql = """
    INSERT INTO leads (place_id, name, city, address, phone, website, email, rating, total_reviews, business_status, source)
    VALUES (:place_id, :name, :city, :address, :phone, :website, :email, :rating, :total_reviews, :business_status, :source)
    ON CONFLICT(place_id) DO UPDATE SET
        phone    = COALESCE(excluded.phone, leads.phone),
        website  = COALESCE(excluded.website, leads.website),
        email    = COALESCE(excluded.email, leads.email),
        rating   = excluded.rating,
        total_reviews = excluded.total_reviews
    """
    with get_connection() as conn:
        conn.execute(sql, lead)
        conn.commit()


def get_all_leads() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY city, name").fetchall()
        return [dict(row) for row in rows]


def get_unsynced_leads() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE klaviyo_synced = 0 AND (email IS NOT NULL OR phone IS NOT NULL) ORDER BY city, name"
        ).fetchall()
        return [dict(row) for row in rows]


def mark_leads_synced(lead_ids: list[int]):
    if not lead_ids:
        return
    placeholders = ",".join("?" * len(lead_ids))
    with get_connection() as conn:
        conn.execute(
            f"UPDATE leads SET klaviyo_synced = 1 WHERE id IN ({placeholders})",
            lead_ids,
        )
        conn.commit()


CREATE_JOBS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    query         TEXT,
    cities        TEXT,  -- JSON array
    status        TEXT DEFAULT 'running',
    leads_found   INTEGER DEFAULT 0,
    leads_with_email INTEGER DEFAULT 0,
    klaviyo_synced INTEGER DEFAULT 0,
    started_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at   DATETIME,
    duration_seconds REAL,
    error         TEXT
);
"""


def init_jobs_table():
    with get_connection() as conn:
        conn.execute(CREATE_JOBS_TABLE_SQL)
        conn.commit()


def create_job(job_id: str, query: str, cities: list) -> dict:
    import json
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO jobs (id, query, cities) VALUES (?, ?, ?)",
            (job_id, query, json.dumps(cities))
        )
        conn.commit()
    return get_job(job_id)


def get_job(job_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def get_all_jobs() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY started_at DESC").fetchall()
        return [dict(row) for row in rows]


def update_job(job_id: str, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)
        conn.commit()


def export_csv():
    leads = get_all_leads()
    if not leads:
        print("Nenhum lead para exportar.")
        return

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "name", "city", "address", "phone",
        "website", "email", "rating", "total_reviews",
        "business_status", "source", "status", "created_at",
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)

    print(f"\nCSV exportado: {CSV_PATH} ({len(leads)} leads)")
