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
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


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
