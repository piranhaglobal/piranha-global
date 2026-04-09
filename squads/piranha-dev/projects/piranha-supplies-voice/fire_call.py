#!/usr/bin/env python3
"""
Disparo manual de ligação para um checkout abandonado específico.

Uso:
    python fire_call.py 36031105368169
    python fire_call.py 36031105368169 --dry-run   # mostra dados sem ligar

Bypassa: janela de horas, filtro UE, check de já chamado.
Útil para: testes manuais, reprocessar leads específicos.
"""

import argparse
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.clients.shopify import ShopifyClient
from src.handlers.call_handler import process_single, _build_call_context
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def find_checkout(client: ShopifyClient, checkout_id: str) -> dict | None:
    """Procura o checkout pelo ID varrendo janelas de tempo."""
    for days_back in [14, 30, 60, 90]:
        now = datetime.now(timezone.utc)
        created_at_min = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = client._make_request("GET", "/checkouts.json", params={
            "status": "open",
            "limit": 250,
            "created_at_min": created_at_min,
        })
        for c in raw.get("checkouts", []):
            if str(c.get("id", "")) == checkout_id:
                return c
    return None


def extract_with_phone_fallback(client: ShopifyClient, raw: dict) -> dict:
    """
    Extrai contacto com fallback de telefone para shipping_address.
    O _extract_contact padrão não lê shipping_address.phone — este wrapper corrige.
    """
    contact = client._extract_contact(raw)

    if not contact["phone"]:
        shipping = raw.get("shipping_address") or raw.get("billing_address") or {}
        fallback = shipping.get("phone", "").strip()
        if fallback:
            print(f"  [fallback] telefone obtido de shipping_address: {fallback}")
            contact["phone"] = fallback

    return contact


def main() -> None:
    parser = argparse.ArgumentParser(description="Disparo manual de ligação")
    parser.add_argument("checkout_id", help="ID numérico do checkout Shopify")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra contexto da ligação sem disparar")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  PIRANHA SUPPLIES VOICE — Disparo Manual")
    print(f"  Checkout: #{args.checkout_id}")
    print(f"  Modo: {'DRY RUN (sem ligação)' if args.dry_run else 'LIGAÇÃO REAL'}")
    print(f"{'='*60}\n")

    client = ShopifyClient()

    print(f"A buscar checkout #{args.checkout_id} no Shopify...")
    raw = find_checkout(client, args.checkout_id)
    if not raw:
        print(f"ERRO: Checkout {args.checkout_id} não encontrado.")
        sys.exit(1)

    contact = extract_with_phone_fallback(client, raw)

    print(f"\n  Nome:     {contact['name']}")
    print(f"  Telefone: {contact['phone'] or 'VAZIO — não é possível ligar'}")
    print(f"  País:     {contact['country_code']}")
    print(f"  Total:    {contact['total_price']} €")
    print(f"  Produtos: {len(contact['products'])}")
    for p in contact["products"]:
        print(f"    - {p['title']} ({p['price']}€)")

    if not contact["phone"]:
        print("\nERRO: Checkout sem telefone. Não é possível ligar.")
        sys.exit(1)

    if args.dry_run:
        print("\n[DRY RUN] A construir contexto da ligação...")
        ctx = _build_call_context(contact)
        print(f"\n  Idioma:  {ctx['language']}")
        print(f"  Voz:     {ctx['voice']}")
        print(f"  Hint:    {ctx['language_hint']}")
        print(f"\n  System prompt ({len(ctx['system_prompt'])} chars):")
        print("  " + ctx["system_prompt"][:400].replace("\n", "\n  ") + "...")
        print("\n[DRY RUN] Ligação NÃO disparada.\n")
        return

    print(f"\nA disparar ligação para {contact['phone']}...")
    call_done = threading.Event()
    status = process_single(contact, call_done)

    if status == "called":
        print(f"\n  Ligação iniciada com sucesso!")
        print(f"  A aguardar conclusão da chamada...")
        call_done.wait(timeout=300)  # timeout 5 min
        print(f"  Chamada concluída.\n")
    else:
        print(f"\n  ERRO ao disparar ligação (status: {status})\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
