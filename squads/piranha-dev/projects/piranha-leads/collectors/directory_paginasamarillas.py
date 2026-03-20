from collectors.firecrawl_extractor import fetch_with_firecrawl
from bs4 import BeautifulSoup


def collect_from_paginasamarillas(city: str, query: str = "estudio de tatuaje") -> list[dict]:
    """
    Extrai leads do Páginas Amarillas usando Firecrawl.
    Requer que o Firecrawl esteja rodando via Docker.
    """
    city_slug = city.lower().replace(" ", "-").replace("á", "a").replace("é", "e") \
        .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    query_slug = query.lower().replace(" ", "-")

    url = f"https://www.paginasamarillas.es/search/{query_slug}/all-{city_slug}/"
    print(f"  [PAginas Amarillas] Buscando em {url}")

    html = fetch_with_firecrawl(url, wait_for=5000)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    leads = []

    for card in soup.select(".listado-item, .list-item, article.item"):
        name_elem = card.select_one(".nombre, .name, h2, h3")
        phone_elem = card.select_one(".telefono, .phone, [data-phone]")
        web_elem = card.select_one("a.web, a[href*='http']:not([href*='paginasamarillas'])")
        address_elem = card.select_one(".direccion, .address, .location")

        lead = {
            "place_id": None,
            "name": name_elem.get_text(strip=True) if name_elem else None,
            "city": city,
            "address": address_elem.get_text(strip=True) if address_elem else None,
            "phone": phone_elem.get_text(strip=True) if phone_elem else None,
            "website": web_elem.get("href") if web_elem else None,
            "email": None,
            "rating": None,
            "total_reviews": None,
            "business_status": "OPERATIONAL",
            "source": "paginasamarillas",
        }

        if lead["name"]:
            leads.append(lead)

    print(f"  [Páginas Amarillas] {len(leads)} leads encontrados em {city}")
    return leads
