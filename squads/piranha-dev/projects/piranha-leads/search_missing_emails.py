#!/usr/bin/env python3
"""
Search for emails on leads that currently don't have one.
Uses the Layer 4 search-based email discovery (Facebook/Instagram).
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env", override=True)

from storage.database import get_all_leads, get_connection
from collectors.google_search_extractor import search_email_for_lead


def search_missing_emails():
    leads = get_all_leads()
    missing_email = [l for l in leads if not l.get("email")]

    print(f"\n{'='*60}")
    print(f"Procurando emails para {len(missing_email)} leads sem email...")
    print(f"{'='*60}\n")

    found = 0
    failed_searches = 0

    for i, lead in enumerate(missing_email, 1):
        lead_id = lead["id"]
        name = lead.get("name", "").strip()
        city = lead.get("city", "").strip() or "Spain"

        if not name:
            print(f"[{i}/{len(missing_email)}] ⊘ ID {lead_id}: sem nome, pulando")
            continue

        print(f"[{i}/{len(missing_email)}] 🔍 {name} ({city})...", end=" ", flush=True)

        try:
            email = search_email_for_lead(name, city)
            if email:
                # Atualiza DB
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE leads SET email = ? WHERE id = ?",
                        (email, lead_id)
                    )
                    conn.commit()
                print(f"✓ {email}")
                found += 1
            else:
                print("—")
        except Exception as e:
            print(f"[erro: {str(e)[:40]}]")
            failed_searches += 1

    print(f"\n{'='*60}")
    print(f"Resultados:")
    print(f"  Emails encontrados: {found}")
    print(f"  Erros de pesquisa:  {failed_searches}")
    print(f"  Sem email ainda:    {len(missing_email) - found}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    search_missing_emails()
