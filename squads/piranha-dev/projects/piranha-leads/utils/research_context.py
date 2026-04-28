import re
import unicodedata

from config import SPAIN_CITIES


COUNTRY_CITIES = {
    "es": SPAIN_CITIES,
    "pt": [
        "Lisboa", "Porto", "Braga", "Coimbra", "Aveiro", "Faro", "Setúbal",
        "Funchal", "Ponta Delgada", "Viseu", "Leiria", "Évora", "Beja",
        "Viana do Castelo", "Guimarães", "Vila Real", "Bragança",
        "Castelo Branco", "Portalegre", "Santarém", "Almada", "Lagos",
        "Covilhã", "Barcelos",
    ],
    "fr": [
        "Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes",
        "Strasbourg", "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims",
        "Le Havre", "Saint-Étienne", "Toulon", "Grenoble", "Dijon", "Angers",
    ],
    "it": [
        "Roma", "Milano", "Napoli", "Torino", "Palermo", "Genova",
        "Bologna", "Firenze", "Bari", "Catania", "Venezia", "Verona",
        "Messina", "Padova", "Trieste", "Taranto", "Brescia", "Prato",
    ],
    "de": [
        "Berlin", "Hamburg", "München", "Köln", "Frankfurt am Main",
        "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund", "Essen",
        "Bremen", "Dresden", "Hannover", "Nürnberg", "Duisburg", "Bochum",
    ],
    "nl": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Tilburg", "Groningen"],
    "be": ["Brussels", "Antwerp", "Ghent", "Charleroi", "Liège", "Bruges", "Namur", "Leuven"],
}

COUNTRY_ALIASES = {
    "espanha": ("es", "Espanha"),
    "spain": ("es", "Espanha"),
    "portugal": ("pt", "Portugal"),
    "franca": ("fr", "França"),
    "frança": ("fr", "França"),
    "france": ("fr", "França"),
    "italia": ("it", "Itália"),
    "itália": ("it", "Itália"),
    "italy": ("it", "Itália"),
    "alemanha": ("de", "Alemanha"),
    "germany": ("de", "Alemanha"),
    "paises baixos": ("nl", "Países Baixos"),
    "países baixos": ("nl", "Países Baixos"),
    "netherlands": ("nl", "Países Baixos"),
    "belgica": ("be", "Bélgica"),
    "bélgica": ("be", "Bélgica"),
    "belgium": ("be", "Bélgica"),
}

CATEGORIES = [
    {
        "category": "tattoo",
        "query": "estudio de tatuaje",
        "terms": ["tattoo", "tatuagem", "tatuaje", "studio de tattoo", "estudio de tatuaje"],
    },
    {
        "category": "estetica",
        "query": "clinica de estetica",
        "terms": ["estetica", "estética", "clinica de estetica", "clínica de estética", "aesthetics"],
    },
    {
        "category": "dentaria",
        "query": "clinica dentaria",
        "terms": ["dentaria", "dentária", "dentista", "dental", "clinica dental"],
    },
    {
        "category": "bodypiercing",
        "query": "body piercing studio",
        "terms": ["piercing", "bodypiercing", "body piercing"],
    },
]


def _normalize(text: str) -> str:
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", no_accents).strip()


def _extract_category(text: str) -> tuple[str | None, str | None]:
    normalized = _normalize(text)
    for item in CATEGORIES:
        if any(_normalize(term) in normalized for term in item["terms"]):
            return item["category"], item["query"]
    return None, None


def _extract_numbers(text: str) -> tuple[int | None, int | None]:
    normalized = _normalize(text)
    leads_per_city = None
    min_reviews = None

    lead_patterns = [
        r"(\d+)\s+(?:leads?|studios?|clinicas?|cl[ií]nicas?|negocios?|negócios?)\s+(?:por|para cada|em cada)\s+cidade",
        r"(?:quero|buscar|extrair|procura(?:r)?)\s+(\d+)\s+(?:leads?|studios?|clinicas?|cl[ií]nicas?)",
        r"(\d+)\s+(?:por|em cada)\s+cidade",
    ]
    for pattern in lead_patterns:
        match = re.search(pattern, normalized)
        if match:
            leads_per_city = int(match.group(1))
            break

    review_patterns = [
        r"(?:\+|>|mais de|acima de)\s*(\d+)\s+reviews?",
        r"(\d+)\s*\+\s*reviews?",
        r"reviews?\s*(?:\+|>|mais de|acima de)\s*(\d+)",
    ]
    for pattern in review_patterns:
        match = re.search(pattern, normalized)
        if match:
            min_reviews = int(match.group(1))
            break

    return leads_per_city, min_reviews


def _extract_region_and_cities(text: str) -> tuple[str | None, list[str]]:
    normalized = _normalize(text)
    for alias, (code, label) in COUNTRY_ALIASES.items():
        if _normalize(alias) in normalized:
            return label, COUNTRY_CITIES.get(code, [])

    matched_cities: list[str] = []
    for cities in COUNTRY_CITIES.values():
        for city in cities:
            if _normalize(city) in normalized:
                matched_cities.append(city)

    if matched_cities:
        return "Cidades selecionadas", sorted(set(matched_cities))
    return None, []


def merge_context(existing: dict | None, text: str) -> dict:
    existing = existing or {}
    category, query = _extract_category(text)
    leads_per_city, min_reviews = _extract_numbers(text)
    region, cities = _extract_region_and_cities(text)

    context = {
        "category": category or existing.get("category"),
        "query": query or existing.get("query"),
        "region": region or existing.get("region"),
        "region_band_id": existing.get("region_band_id"),
        "cities": cities or existing.get("cities") or [],
        "leads_per_city": leads_per_city or existing.get("leads_per_city"),
        "min_reviews": min_reviews or existing.get("min_reviews"),
        "objective": existing.get("objective") or "Encontrar email e telefone do estabelecimento",
        "klaviyo_list_id": existing.get("klaviyo_list_id"),
        "execution_mode": existing.get("execution_mode") or "plan",
    }

    missing_fields = []
    if not context["category"]:
        missing_fields.append("category")
    if not context["cities"]:
        missing_fields.append("region_or_cities")
    if not context["leads_per_city"]:
        missing_fields.append("leads_per_city")
    if not context["min_reviews"]:
        missing_fields.append("min_reviews")
    if not context["klaviyo_list_id"]:
        missing_fields.append("klaviyo_list_id")
    context["missing_fields"] = missing_fields
    return context


def context_to_brief_text(context: dict) -> str:
    cities = context.get("cities") or []
    city_preview = ", ".join(cities[:8])
    if len(cities) > 8:
        city_preview += f" + {len(cities) - 8} cidades"
    return (
        f"Categoria: {context.get('category') or '-'}\n"
        f"Query: {context.get('query') or '-'}\n"
        f"Região: {context.get('region') or '-'}\n"
        f"Cidades: {city_preview or '-'}\n"
        f"Leads por cidade: {context.get('leads_per_city') or '-'}\n"
        f"Reviews mínimas: {context.get('min_reviews') or '-'}\n"
        f"Objetivo: {context.get('objective') or '-'}\n"
        f"Lista Klaviyo: {context.get('klaviyo_list_id') or '-'}"
        f"\nModo: {context.get('execution_mode') or 'plan'}"
    )
