"""
Script standalone de validação de contactos.
Percorre todos os leads da DB, valida website/email/telefone
e limpa os campos que não são reais.

Uso:
  python3 validate_leads.py              # valida todos os leads não validados
  python3 validate_leads.py --all        # re-valida mesmo os já validados
  python3 validate_leads.py --id 678     # valida um lead específico
  python3 validate_leads.py --dry-run    # mostra o que mudaria sem gravar
"""

import sys
import argparse
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "leads.db"

from validators.contact_validator import validate_lead_contacts
from storage.database import get_connection

# Adicionar coluna validated_at se não existir
def _ensure_validated_column():
    with get_connection() as conn:
        try:
            conn.execute("ALTER TABLE leads ADD COLUMN validated_at DATETIME")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # já existe


def _get_leads_to_validate(lead_id: int | None, revalidate: bool) -> list[dict]:
    with get_connection() as conn:
        if lead_id:
            rows = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchall()
        elif revalidate:
            rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads WHERE validated_at IS NULL ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]


def _update_lead(lead_id: int, website, email, phone):
    with get_connection() as conn:
        conn.execute(
            """UPDATE leads
               SET website = ?, email = ?, phone = ?,
                   validated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (website, email, phone, lead_id),
        )
        conn.commit()


def run(lead_id=None, revalidate=False, dry_run=False):
    _ensure_validated_column()
    leads = _get_leads_to_validate(lead_id, revalidate)

    if not leads:
        print("Nenhum lead para validar.")
        return

    total = len(leads)
    changed = 0
    cleared_website = 0
    cleared_email = 0
    cleared_phone = 0

    print(f"A validar {total} leads{'  [DRY RUN — sem gravação]' if dry_run else ''}...\n")

    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "?")
        city = lead.get("city", "?")
        has_data = lead.get("website") or lead.get("email") or lead.get("phone")

        if not has_data:
            if not dry_run:
                _update_lead(lead["id"], None, None, None)
            continue

        print(f"[{i}/{total}] {name} ({city})")
        result = validate_lead_contacts(lead, verbose=True)
        clean = result["clean"]

        website_changed = clean["website"] != lead.get("website")
        email_changed   = clean["email"]   != lead.get("email")
        phone_changed   = clean["phone"]   != lead.get("phone")

        if website_changed:
            cleared_website += 1
            print(f"  → website: {lead.get('website')} ✗ limpo")
        if email_changed:
            cleared_email += 1
            print(f"  → email: {lead.get('email')} ✗ limpo")
        if phone_changed:
            cleared_phone += 1
            print(f"  → phone: {lead.get('phone')} ✗ limpo")

        if website_changed or email_changed or phone_changed:
            changed += 1
            if not dry_run:
                _update_lead(lead["id"], clean["website"], clean["email"], clean["phone"])

    print(f"\n{'=' * 60}")
    print(f"Validação concluída {'[DRY RUN]' if dry_run else ''}!")
    print(f"  Total validados:      {total}")
    print(f"  Leads com alterações: {changed}")
    print(f"  Websites limpos:      {cleared_website}")
    print(f"  Emails limpos:        {cleared_email}")
    print(f"  Telefones limpos:     {cleared_phone}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida contactos dos leads na DB")
    parser.add_argument("--all", action="store_true", help="Re-valida todos (incl. já validados)")
    parser.add_argument("--id", type=int, help="Valida apenas o lead com este ID")
    parser.add_argument("--dry-run", action="store_true", help="Mostra alterações sem gravar")
    args = parser.parse_args()

    run(lead_id=args.id, revalidate=args.all, dry_run=args.dry_run)
