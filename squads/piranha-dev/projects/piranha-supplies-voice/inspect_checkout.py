#!/usr/bin/env python3
"""
Inspeciona um checkout abandonado do Shopify e mostra todos os dados dinâmicos
que seriam enviados para o agente de voz.

Uso:
    python inspect_checkout.py                          # mais recente com telefone
    python inspect_checkout.py 36031105368169
    python inspect_checkout.py 36031105368169 --lang pt
    python inspect_checkout.py 36031105368169 --prompt  # mostra system prompt completo
"""

import argparse
import json
import sys
from pathlib import Path

# Adicionar src/ ao path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.clients.shopify import ShopifyClient
from src.utils.language_detector import get_language, get_voice_for_language
from src.handlers.call_handler import (
    _format_products,
    _format_product_details,
    _format_value,
    _format_date,
    _format_days,
)
from src.prompts.feedback_agent import build_system_prompt


def find_checkout(client: ShopifyClient, checkout_id: str) -> dict | None:
    """Procura o checkout pelo ID varrendo as páginas da API."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    # Tentar janelas de tempo crescentes
    for days_back in [14, 30, 60, 90]:
        created_at_min = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = client._make_request("GET", "/checkouts.json", params={
            "status": "open",
            "limit": 250,
            "created_at_min": created_at_min,
        })
        for c in raw.get("checkouts", []):
            if str(c.get("id", "")) == checkout_id:
                return c

    # Última tentativa: sem filtro de data
    raw = client._make_request("GET", "/checkouts.json", params={
        "status": "open",
        "limit": 250,
    })
    for c in raw.get("checkouts", []):
        if str(c.get("id", "")) == checkout_id:
            return c

    return None


def sep(title: str = "") -> None:
    width = 72
    if title:
        print(f"\n{'─' * 3} {title} {'─' * (width - len(title) - 5)}")
    else:
        print("─" * width)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspecionar checkout abandonado")
    parser.add_argument("checkout_id", nargs="?", default=None,
                        help="ID numérico do checkout. Se omitido, usa o mais recente com telefone.")
    parser.add_argument("--lang", default=None, help="Forçar idioma: pt, es, fr, en")
    parser.add_argument("--prompt", action="store_true", help="Mostrar system prompt completo")
    parser.add_argument("--json", action="store_true", help="Output em JSON (para debug)")
    args = parser.parse_args()

    client = ShopifyClient()

    # 1. Encontrar checkout raw
    if args.checkout_id:
        print(f"\n🔍 A buscar checkout #{args.checkout_id} no Shopify...")
        raw = find_checkout(client, args.checkout_id)
        if not raw:
            print(f"❌ Checkout {args.checkout_id} não encontrado (status=open).")
            sys.exit(1)
    else:
        print("\n🔍 A buscar checkout mais recente com telefone...")
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        created_at_min = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        resp = client._make_request("GET", "/checkouts.json", params={
            "status": "open", "limit": 250, "created_at_min": created_at_min,
        })
        raw = None
        for c in reversed(resp.get("checkouts", [])):
            phone = (c.get("phone") or
                     c.get("customer", {}).get("phone") or
                     (c.get("shipping_address") or {}).get("phone") or "")
            if phone:
                raw = c
                break
        if not raw:
            print("❌ Nenhum checkout com telefone encontrado nos últimos 90 dias.")
            sys.exit(1)
        print(f"   → Encontrado: #{raw['id']}")

    # 2. Extrair contacto + enriquecer produtos via Shopify
    contact = client._extract_contact(raw)

    sep("CHECKOUT RAW — dados básicos")
    print(f"  ID:           {contact['id']}")
    print(f"  Nome:         {contact['name']}")
    print(f"  Telefone:     {contact['phone'] or '⚠️  VAZIO (não elegível para chamada live!)'}")
    print(f"  País:         {contact['country_code']}")
    print(f"  Total:        {contact['total_price']} €")
    print(f"  Criado em:    {contact['created_at']}")
    print(f"  Produtos:     {len(contact['products'])}")

    # Verificar elegibilidade
    if not contact['phone']:
        # Tentar extrair de shipping/billing address
        shipping = raw.get("shipping_address") or raw.get("billing_address") or {}
        fallback_phone = shipping.get("phone", "")
        if fallback_phone:
            print(f"\n  ⚠️  phone nulo no checkout/customer, mas encontrado em shipping_address: {fallback_phone}")
            contact['phone'] = fallback_phone
        else:
            print(f"\n  ⚠️  Este checkout NÃO seria chamado no sistema live (sem telefone).")

    # 3. Determinar idioma
    language = args.lang or get_language(contact["country_code"])
    voice = get_voice_for_language(language)

    sep("IDIOMA & VOZ")
    print(f"  Idioma:  {language}")
    print(f"  Voz:     {voice}")

    # 4. Mostrar produtos com todos os dados enriquecidos
    sep("PRODUTOS ENRIQUECIDOS (description + product_details + FAQs)")
    for i, p in enumerate(contact["products"], 1):
        print(f"\n  [{i}] {p['title']}")
        print(f"       Marca:   {p.get('vendor', '-')}")
        print(f"       Preço:   {p.get('price', '-')} €")
        print(f"       URL:     {p.get('url') or '(sem URL)'}")

        desc = p.get("description", "").strip()
        details = p.get("product_details", "").strip()
        faqs = p.get("faqs", [])

        print(f"\n       📝 description ({len(desc)} chars):")
        print(f"       {desc[:300] + '...' if len(desc) > 300 else desc or '(vazio)'}")

        print(f"\n       🔧 product_details ({len(details)} chars):")
        print(f"       {details[:300] + '...' if len(details) > 300 else details or '(vazio)'}")

        print(f"\n       ❓ FAQs: {len(faqs)} extraídas")
        for j, faq in enumerate(faqs[:3], 1):
            print(f"          Q{j}: {faq.get('question', '')[:80]}")
            print(f"          A{j}: {faq.get('answer', '')[:80]}")
        if len(faqs) > 3:
            print(f"          ... +{len(faqs) - 3} FAQs adicionais")

    # 5. Formatar para voz
    sep("FORMATAÇÃO PARA VOZ")
    cart_products = _format_products(contact["products"], language)
    cart_value = _format_value(contact["total_price"], language)
    abandon_date = _format_date(contact["created_at"], language)
    days_since = _format_days(contact["created_at"], language)
    product_details_block = _format_product_details(contact["products"], language)

    print(f"  cart_products:      {cart_products}")
    print(f"  cart_value:         {cart_value}")
    print(f"  abandon_date:       {abandon_date}")
    print(f"  days_since_abandon: {days_since}")
    print(f"\n  product_details block ({len(product_details_block)} chars):")
    print("  " + "\n  ".join(product_details_block[:800].splitlines()))
    if len(product_details_block) > 800:
        print(f"  ... (truncado — total {len(product_details_block)} chars)")

    # 6. System prompt completo (opcional)
    if args.prompt:
        sep("SYSTEM PROMPT COMPLETO")
        system_prompt = build_system_prompt(
            lead_name=contact["name"],
            cart_products=cart_products,
            cart_value=cart_value,
            abandon_date=abandon_date,
            days_since_abandon=days_since,
            product_details=product_details_block,
            language=language,
        )
        print(system_prompt)

    # 7. JSON dump (opcional)
    if args.json:
        sep("JSON COMPLETO DO CONTACT")
        print(json.dumps(contact, ensure_ascii=False, indent=2))

    sep()
    print("✅ Inspecção concluída.\n")


if __name__ == "__main__":
    main()
