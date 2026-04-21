import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(override=True)

from config import SPAIN_CITIES, REQUEST_DELAY, MIN_REVIEWS, MAX_LEADS_PER_CITY
from collectors.google_places import search_studios_in_city, get_place_details
from collectors.email_extractor import extract_email_from_website
from collectors.directory_paginasamarillas import collect_from_paginasamarillas
from collectors.firecrawl_extractor import firecrawl_available
from collectors.instagram_extractor import extract_email_from_instagram
from collectors.google_search_extractor import search_email_for_lead
from storage.database import init_db, upsert_lead, export_csv, get_unsynced_leads, mark_leads_synced
from integrations.klaviyo import sync_leads_to_klaviyo


def run(progress_callback=None, cities_override=None, query_override=None):
    from config import SEARCH_QUERY
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("Erro: GOOGLE_PLACES_API_KEY não encontrada no .env")
        sys.exit(1)

    init_db()

    cities = cities_override if cities_override else SPAIN_CITIES
    query = query_override if query_override else SEARCH_QUERY

    use_firecrawl = firecrawl_available()
    if use_firecrawl:
        print("Firecrawl detectado — fallback de email e Páginas Amarillas ativos.\n")
    else:
        print("Firecrawl nao detectado — usando apenas Google Places + extrator simples.\n")
        print("  Para ativar: docker-compose up -d\n")

    total_leads = 0
    total_with_email = 0
    total_with_phone = 0

    print(f"Iniciando coleta em {len(cities)} capitais de província da Espanha...")
    print(f"Critério: {MIN_REVIEWS}+ reviews · máx {MAX_LEADS_PER_CITY} studios por cidade\n")

    for i, city in enumerate(cities, start=1):
        print(f"[{i}/{len(cities)}] {city}")

        if progress_callback:
            progress_callback("city_start", {"city": city, "city_index": i, "total_cities": len(cities)})

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
            if progress_callback:
                progress_callback("city_progress", {"city": city, "city_index": i, "total_cities": len(cities), "leads_found": 0, "leads_with_email": 0})
            continue

        # Filtra por reviews mínimas e limita ao máximo por cidade
        qualified = [
            s for s in all_studios
            if (s.get("total_reviews") or 0) >= MIN_REVIEWS
        ]
        qualified.sort(key=lambda s: s.get("total_reviews") or 0, reverse=True)
        qualified = qualified[:MAX_LEADS_PER_CITY]

        total_candidates = len(all_studios)
        print(f"  → {total_candidates} encontrados · {len(qualified)} com {MIN_REVIEWS}+ reviews")

        if not qualified:
            print(f"  → Nenhum studio com {MIN_REVIEWS}+ reviews nesta cidade.")
            if progress_callback:
                progress_callback("city_progress", {"city": city, "city_index": i, "total_cities": len(cities), "leads_found": 0, "leads_with_email": 0})
            continue

        for studio in qualified:
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

            # Fallback: Instagram bio scraping (quando website não tem email)
            if not studio.get("email") and studio.get("website"):
                try:
                    ig_email = extract_email_from_instagram(studio["website"])
                    if ig_email:
                        studio["email"] = ig_email
                except Exception as e:
                    print(f"    [!] Instagram scraping erro para '{name}': {e}")

            # Fallback: Search-based discovery (Facebook/Instagram via DuckDuckGo)
            if not studio.get("email"):
                try:
                    searched_email = search_email_for_lead(name, city)
                    if searched_email:
                        studio["email"] = searched_email
                        print(f"    [search] Email encontrado via pesquisa: {searched_email}")
                except Exception as e:
                    print(f"    [!] Search email erro para '{name}': {e}")

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

        if progress_callback:
            progress_callback("city_progress", {
                "city": city,
                "city_index": i,
                "total_cities": len(cities),
                "leads_found": len(qualified),
                "leads_with_email": sum(1 for s in qualified if s.get("email"))
            })

        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"Coleta concluída!")
    print(f"  Total de leads:        {total_leads}")
    print(f"  Com telefone:          {total_with_phone} ({_pct(total_with_phone, total_leads)}%)")
    print(f"  Com email:             {total_with_email} ({_pct(total_with_email, total_leads)}%)")
    print("=" * 60)

    export_csv()

    # --- Klaviyo sync ---
    klaviyo_list_id = os.getenv("KLAVIYO_LIST_ID", "S9Qa55")
    klaviyo_key = os.getenv("KLAVIYO_PRIVATE_API_KEY")
    if klaviyo_key:
        if progress_callback:
            progress_callback("klaviyo_start", {"total_leads": total_leads})
        print("\nSincronizando leads novos com Klaviyo...")
        unsynced = get_unsynced_leads()
        if unsynced:
            result = sync_leads_to_klaviyo(unsynced, klaviyo_list_id)
            if result["synced"] > 0:
                synced_ids = [l["id"] for l in unsynced]
                mark_leads_synced(synced_ids)
            print(f"  Klaviyo: {result['synced']} sincronizados, {result['skipped']} sem contacto.")
            if progress_callback:
                progress_callback("job_complete", {"total_leads": total_leads, "klaviyo_synced": result.get("synced", 0)})
        else:
            print("  Klaviyo: nenhum lead novo para sincronizar.")
            if progress_callback:
                progress_callback("job_complete", {"total_leads": total_leads, "klaviyo_synced": 0})
    else:
        print("\n[!] KLAVIYO_PRIVATE_API_KEY não definida — sync ignorado.")
        if progress_callback:
            progress_callback("job_complete", {"total_leads": total_leads, "klaviyo_synced": 0})


def _pct(part: int, total: int) -> int:
    if total == 0:
        return 0
    return round((part / total) * 100)


if __name__ == "__main__":
    run()
