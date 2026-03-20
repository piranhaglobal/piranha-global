import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

from config import SPAIN_CITIES, REQUEST_DELAY
from collectors.google_places import search_studios_in_city, get_place_details
from collectors.email_extractor import extract_email_from_website
from collectors.directory_paginasamarillas import collect_from_paginasamarillas
from collectors.firecrawl_extractor import firecrawl_available
from storage.database import init_db, upsert_lead, export_csv


def run():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("Erro: GOOGLE_PLACES_API_KEY não encontrada no .env")
        sys.exit(1)

    init_db()

    use_firecrawl = firecrawl_available()
    if use_firecrawl:
        print("Firecrawl detectado — fallback de email e Páginas Amarillas ativos.\n")
    else:
        print("Firecrawl nao detectado — usando apenas Google Places + extrator simples.\n")
        print("  Para ativar: docker-compose up -d\n")

    total_leads = 0
    total_with_email = 0
    total_with_phone = 0

    print(f"Iniciando coleta em {len(SPAIN_CITIES)} cidades da Espanha...\n")

    for i, city in enumerate(SPAIN_CITIES, start=1):
        print(f"[{i}/{len(SPAIN_CITIES)}] {city}")

        all_studios = []

        # --- Fonte 1: Google Places ---
        try:
            places_results = search_studios_in_city(city, api_key)
            for s in places_results:
                s["source"] = "google_places"
            all_studios.extend(places_results)
        except Exception as e:
            print(f"  [!] Google Places erro em {city}: {e}")

        # --- Fonte 2: Páginas Amarillas (requer Firecrawl) ---
        if use_firecrawl:
            try:
                pa_results = collect_from_paginasamarillas(city)
                all_studios.extend(pa_results)
            except Exception as e:
                print(f"  [!] Páginas Amarillas erro em {city}: {e}")

        if not all_studios:
            print(f"  → Nenhum resultado encontrado.")
            continue

        for studio in all_studios:
            name = studio.get("name", "sem nome")

            # Busca detalhes adicionais no Google Places (só para leads do Places)
            if studio.get("source") == "google_places" and studio.get("place_id"):
                try:
                    details = get_place_details(studio["place_id"], api_key)
                    studio["phone"] = details.get("phone") or studio.get("phone")
                    studio["website"] = details.get("website") or studio.get("website")
                    time.sleep(REQUEST_DELAY)
                except Exception as e:
                    print(f"    [!] Details erro para '{name}': {e}")

            # Extração de email via website
            if studio.get("website"):
                try:
                    studio["email"] = extract_email_from_website(
                        studio["website"],
                        use_firecrawl_fallback=use_firecrawl,
                    )
                except Exception as e:
                    print(f"    [!] Email erro para '{name}': {e}")

            # Garante que place_id de diretórios não colidam com os do Google
            if not studio.get("place_id"):
                studio["place_id"] = f"{studio.get('source','dir')}_{city}_{name}".replace(" ", "_").lower()

            # Garante campos obrigatórios com defaults
            studio.setdefault("email", None)
            studio.setdefault("phone", None)
            studio.setdefault("website", None)
            studio.setdefault("rating", None)
            studio.setdefault("total_reviews", None)
            studio.setdefault("business_status", "OPERATIONAL")
            studio.setdefault("source", "unknown")

            upsert_lead(studio)
            total_leads += 1

            if studio.get("email"):
                total_with_email += 1
            if studio.get("phone"):
                total_with_phone += 1

            status_parts = []
            if studio.get("phone"):
                status_parts.append(f"tel: {studio['phone']}")
            if studio.get("email"):
                status_parts.append(f"email: {studio['email']}")
            status_str = " | ".join(status_parts) if status_parts else "sem contacto direto"

            print(f"  ✓ [{studio.get('source','?')}] {name} — {status_str}")

        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"Coleta concluída!")
    print(f"  Total de leads:        {total_leads}")
    print(f"  Com telefone:          {total_with_phone} ({_pct(total_with_phone, total_leads)}%)")
    print(f"  Com email:             {total_with_email} ({_pct(total_with_email, total_leads)}%)")
    print("=" * 60)

    export_csv()


def _pct(part: int, total: int) -> int:
    if total == 0:
        return 0
    return round((part / total) * 100)


if __name__ == "__main__":
    run()
