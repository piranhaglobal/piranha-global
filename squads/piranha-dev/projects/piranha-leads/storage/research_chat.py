import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from storage.database import get_connection


def _now() -> str:
    return datetime.utcnow().isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    for key in ("cities_json", "payload_json", "entities_json", "result_summary"):
        if key in item:
            fallback = [] if key == "cities_json" else {}
            item[key.replace("_json", "")] = _load_json(item.pop(key), fallback)
    return item


CREATE_CHAT_THREADS_SQL = """
CREATE TABLE IF NOT EXISTS chat_threads (
    id              TEXT PRIMARY KEY,
    folder_id       TEXT,
    title           TEXT NOT NULL,
    status          TEXT DEFAULT 'active',
    usable_for_cron INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CHAT_FOLDERS_SQL = """
CREATE TABLE IF NOT EXISTS chat_folders (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CHAT_MESSAGES_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    audio_path  TEXT,
    transcript  TEXT,
    model       TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES chat_threads(id)
);
"""

CREATE_CHAT_CONTEXTS_SQL = """
CREATE TABLE IF NOT EXISTS chat_contexts (
    thread_id           TEXT PRIMARY KEY,
    category            TEXT,
    region              TEXT,
    region_band_id      TEXT,
    cities_json         TEXT,
    leads_per_city      INTEGER,
    min_reviews         INTEGER,
    query               TEXT,
    objective           TEXT,
    klaviyo_list_id     TEXT,
    completeness_status TEXT DEFAULT 'incomplete',
    missing_fields      TEXT,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES chat_threads(id)
);
"""

CREATE_RESEARCH_BRIEFS_SQL = """
CREATE TABLE IF NOT EXISTS research_briefs (
    id              TEXT PRIMARY KEY,
    thread_id       TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    status          TEXT DEFAULT 'created',
    executed_job_id TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES chat_threads(id)
);
"""

CREATE_RESEARCH_LOG_SQL = """
CREATE TABLE IF NOT EXISTS research_log (
    id              TEXT PRIMARY KEY,
    dedupe_key      TEXT UNIQUE,
    thread_id       TEXT,
    brief_id        TEXT,
    job_id          TEXT,
    region          TEXT,
    category        TEXT,
    query           TEXT,
    leads_per_city  INTEGER,
    min_reviews     INTEGER,
    cities_json     TEXT,
    status          TEXT DEFAULT 'created',
    result_summary  TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def init_research_chat_tables() -> None:
    with get_connection() as conn:
        conn.execute(CREATE_CHAT_FOLDERS_SQL)
        conn.execute(CREATE_CHAT_THREADS_SQL)
        conn.execute(CREATE_CHAT_MESSAGES_SQL)
        conn.execute(CREATE_CHAT_CONTEXTS_SQL)
        conn.execute(CREATE_RESEARCH_BRIEFS_SQL)
        conn.execute(CREATE_RESEARCH_LOG_SQL)
        try:
            conn.execute("ALTER TABLE chat_threads ADD COLUMN folder_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE chat_contexts ADD COLUMN klaviyo_list_id TEXT")
        except sqlite3.OperationalError:
            pass
        if not conn.execute("SELECT 1 FROM chat_folders WHERE id = 'default'").fetchone():
            conn.execute(
                "INSERT INTO chat_folders (id, name, created_at) VALUES ('default', 'Geral', ?)",
                (_now(),),
            )
        conn.commit()


def create_thread(title: str = "Nova pesquisa", folder_id: str | None = None) -> dict:
    thread_id = str(uuid.uuid4())[:8]
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_threads (id, folder_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (thread_id, folder_id or "default", title.strip() or "Nova pesquisa", now, now),
        )
        conn.commit()
    return get_thread(thread_id)


def get_thread(thread_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chat_threads WHERE id = ?", (thread_id,)).fetchone()
        return dict(row) if row else None


def list_threads() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_threads ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def list_folders() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM chat_folders ORDER BY created_at ASC").fetchall()
        return [dict(row) for row in rows]


def create_folder(name: str) -> dict:
    folder_id = str(uuid.uuid4())[:8]
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_folders (id, name, created_at) VALUES (?, ?, ?)",
            (folder_id, name.strip() or "Novo segmento", _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM chat_folders WHERE id = ?", (folder_id,)).fetchone()
        return dict(row)


def delete_folder(folder_id: str) -> None:
    if folder_id == "default":
        raise ValueError("Default folder cannot be deleted")
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_threads SET folder_id = 'default', updated_at = ? WHERE folder_id = ?",
            (_now(), folder_id),
        )
        conn.execute("DELETE FROM chat_folders WHERE id = ?", (folder_id,))
        conn.commit()


def set_thread_folder(thread_id: str, folder_id: str | None) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_threads SET folder_id = ?, updated_at = ? WHERE id = ?",
            (folder_id or "default", _now(), thread_id),
        )
        conn.commit()


def delete_thread(thread_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM chat_contexts WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM research_briefs WHERE thread_id = ?", (thread_id,))
        conn.execute("UPDATE research_log SET thread_id = NULL WHERE thread_id = ?", (thread_id,))
        conn.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
        conn.commit()


def update_thread_title(thread_id: str, title: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_threads SET title = ?, updated_at = ? WHERE id = ?",
            (title[:80] or "Nova pesquisa", _now(), thread_id),
        )
        conn.commit()


def set_thread_cron_enabled(thread_id: str, enabled: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_threads SET usable_for_cron = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, _now(), thread_id),
        )
        conn.commit()


def add_message(
    thread_id: str,
    role: str,
    content: str,
    model: str | None = None,
    audio_path: str | None = None,
    transcript: str | None = None,
) -> dict:
    msg_id = str(uuid.uuid4())[:10]
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (id, thread_id, role, content, audio_path, transcript, model, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, thread_id, role, content, audio_path, transcript, model, now),
        )
        conn.execute(
            "UPDATE chat_threads SET updated_at = ? WHERE id = ?",
            (now, thread_id),
        )
        conn.commit()
    return get_message(msg_id)


def get_message(message_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
        return dict(row)


def list_messages(thread_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC",
            (thread_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def upsert_context(thread_id: str, context: dict) -> dict:
    missing_fields = context.get("missing_fields") or []
    completeness = "complete" if not missing_fields else "incomplete"
    cities = context.get("cities") or []
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_contexts (
                thread_id, category, region, region_band_id, cities_json, leads_per_city,
                min_reviews, query, objective, klaviyo_list_id, completeness_status, missing_fields, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                category=excluded.category,
                region=excluded.region,
                region_band_id=excluded.region_band_id,
                cities_json=excluded.cities_json,
                leads_per_city=excluded.leads_per_city,
                min_reviews=excluded.min_reviews,
                query=excluded.query,
                objective=excluded.objective,
                klaviyo_list_id=excluded.klaviyo_list_id,
                completeness_status=excluded.completeness_status,
                missing_fields=excluded.missing_fields,
                updated_at=excluded.updated_at
            """,
            (
                thread_id,
                context.get("category"),
                context.get("region"),
                context.get("region_band_id"),
                _json(cities),
                context.get("leads_per_city"),
                context.get("min_reviews"),
                context.get("query"),
                context.get("objective"),
                context.get("klaviyo_list_id"),
                completeness,
                ",".join(missing_fields),
                now,
            ),
        )
        conn.commit()
    return get_context(thread_id)


def clear_context(thread_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_contexts WHERE thread_id = ?", (thread_id,))
        conn.commit()


def get_context(thread_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chat_contexts WHERE thread_id = ?", (thread_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_complete_contexts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*, t.title, t.folder_id, t.usable_for_cron
            FROM chat_contexts c
            JOIN chat_threads t ON t.id = c.thread_id
            WHERE c.completeness_status = 'complete'
              AND t.usable_for_cron = 1
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def list_queued_contexts() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*, t.title, t.folder_id, t.usable_for_cron
            FROM chat_contexts c
            JOIN chat_threads t ON t.id = c.thread_id
            WHERE c.completeness_status = 'complete'
            ORDER BY t.usable_for_cron DESC, c.updated_at DESC
            """
        ).fetchall()
        return [_row_to_dict(row) for row in rows]


def make_dedupe_key(context: dict) -> str:
    cities = context.get("cities") or []
    city_part = ",".join(sorted(city.strip().lower() for city in cities if city.strip()))
    parts = [
        (context.get("region") or "").strip().lower(),
        (context.get("category") or "").strip().lower(),
        (context.get("query") or "").strip().lower(),
        str(context.get("leads_per_city") or ""),
        str(context.get("min_reviews") or ""),
        city_part,
    ]
    return "|".join(parts)


def create_brief(thread_id: str, context: dict) -> dict:
    brief_id = str(uuid.uuid4())[:8]
    payload = {
        "thread_id": thread_id,
        "category": context.get("category"),
        "region": context.get("region"),
        "region_band_id": context.get("region_band_id"),
        "cities": context.get("cities") or [],
        "leads_per_city": context.get("leads_per_city"),
        "min_reviews": context.get("min_reviews"),
        "query": context.get("query"),
        "objective": context.get("objective"),
        "klaviyo_list_id": context.get("klaviyo_list_id"),
        "dedupe_key": make_dedupe_key(context),
    }
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO research_briefs (id, thread_id, payload_json, status, created_at, updated_at)
            VALUES (?, ?, ?, 'created', ?, ?)
            """,
            (brief_id, thread_id, _json(payload), now, now),
        )
        conn.commit()
    return get_brief(brief_id)


def get_brief(brief_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM research_briefs WHERE id = ?", (brief_id,)).fetchone()
        return _row_to_dict(row) if row else None


def update_brief(brief_id: str, **kwargs) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = _now()
    fields = ", ".join(f"{key} = ?" for key in kwargs)
    values = list(kwargs.values()) + [brief_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE research_briefs SET {fields} WHERE id = ?", values)
        conn.commit()


def find_research_log_by_key(dedupe_key: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM research_log WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
        return _row_to_dict(row) if row else None


def create_research_log(thread_id: str, brief_id: str, context: dict, job_id: str | None, status: str) -> dict:
    log_id = str(uuid.uuid4())[:8]
    dedupe_key = make_dedupe_key(context)
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO research_log (
                id, dedupe_key, thread_id, brief_id, job_id, region, category, query,
                leads_per_city, min_reviews, cities_json, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                dedupe_key,
                thread_id,
                brief_id,
                job_id,
                context.get("region"),
                context.get("category"),
                context.get("query"),
                context.get("leads_per_city"),
                context.get("min_reviews"),
                _json(context.get("cities") or []),
                status,
                now,
                now,
            ),
        )
        conn.commit()
    return get_research_log(log_id)


def get_research_log(log_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM research_log WHERE id = ?", (log_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_research_log(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM research_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
