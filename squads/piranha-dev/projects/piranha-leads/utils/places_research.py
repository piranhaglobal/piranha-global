import os
import time
import unicodedata
from typing import Any

from collectors.google_places import search_studios_in_city
from config import SPAIN_CITIES
from utils.research_context import COUNTRY_ALIASES, COUNTRY_CITIES


_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = int(os.getenv("ATLAS_PLACES_INSIGHT_TTL", "1800"))

_SPAIN_NON_CAPITAL_FILTER = {
    "Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga", "Murcia", "Palma",
    "Las Palmas de Gran Canaria", "Bilbao", "Alicante", "Córdoba", "Valladolid", "Granada",
    "Vigo", "Oviedo", "Pamplona", "Santander", "Almería", "Burgos", "Albacete",
    "Castellón de la Plana", "Logroño", "Badajoz", "Salamanca", "Huelva", "Tarragona",
    "Lleida", "León", "Cádiz", "Jaén", "Ourense", "Lugo", "Girona", "Toledo", "Cáceres",
    "Ciudad Real", "Cuenca", "Guadalajara", "Huesca", "Palencia", "Pontevedra", "Segovia",
    "Soria", "Teruel", "Zamora", "Santa Cruz de Tenerife", "Ávila", "Vitoria-Gasteiz",
    "San Sebastián",
}

_DISCOVERY_KEYWORDS = {
    "ideia", "ideias", "briefing", "ranking", "mais em alta", "melhores cidades",
    "onde atacar", "onde começar", "cidades", "potencial", "descobrir", "explorar",
    "pesquisar", "analisar", "mapear",
}


def _normalize(text: str) -> str:
    no_accents = "".join(
        ch for ch in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join(no_accents.split())


def _country_code_from_text(text: str | None) -> str | None:
    if not text:
        return None
    normalized = _normalize(text)
    for alias, (code, _label) in COUNTRY_ALIASES.items():
        if _normalize(alias) in normalized:
            return code
    if "espanha" in normalized or "spain" in normalized:
        return "es"
    if "portugal" in normalized:
        return "pt"
    return None


def _cache_key(context: dict[str, Any], prompt: str | None) -> str:
    cities = ",".join(sorted(context.get("cities") or []))
    return "|".join([
        str(context.get("thread_id") or ""),
        str(context.get("category") or ""),
        str(context.get("region") or ""),
        str(context.get("query") or ""),
        str(context.get("min_reviews") or ""),
        cities,
        str(prompt or ""),
    ])


def should_use_places_intelligence(prompt: str | None, context: dict[str, Any]) -> bool:
    text = _normalize(" ".join(part for part in [prompt or "", context.get("query") or "", context.get("objective") or ""] if part))
    if any(keyword in text for keyword in _DISCOVERY_KEYWORDS):
        return True
    if context.get("category") and context.get("region") and not context.get("cities"):
        return True
    return False


def _pick_candidate_cities(context: dict[str, Any], prompt: str | None, max_cities: int) -> list[str]:
    selected_cities = [city for city in (context.get("cities") or []) if city]
    if selected_cities:
        return selected_cities[:max_cities]

    code = _country_code_from_text(prompt) or _country_code_from_text(context.get("region")) or _country_code_from_text(context.get("query"))
    if code == "es":
        cities = [city for city in SPAIN_CITIES if city not in _SPAIN_NON_CAPITAL_FILTER]
        return cities[:max_cities]

    return (COUNTRY_CITIES.get(code, []) if code else [])[:max_cities]


def build_places_market_snapshot(context: dict[str, Any], prompt: str | None = None, max_cities: int = 8) -> dict[str, Any] | None:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        return {
            "available": False,
            "reason": "GOOGLE_PLACES_API_KEY não configurada",
        }

    query = (context.get("query") or "").strip() or "estudio de tatuaje"
    min_reviews = int(context.get("min_reviews") or 0)
    cities = _pick_candidate_cities(context, prompt, max_cities=max_cities)
    if not cities:
        return {
            "available": False,
            "reason": "Nenhuma cidade candidata disponível para esta região",
        }

    cache_key = _cache_key(context, prompt)
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    city_rows: list[dict[str, Any]] = []
    for city in cities:
        try:
            results = search_studios_in_city(city, api_key, query=query)
        except Exception as exc:
            city_rows.append({
                "city": city,
                "error": str(exc),
                "qualified_count": 0,
                "best_reviews": 0,
                "best_businesses": [],
                "sampled": 0,
                "score": 0,
            })
            continue

        qualified = [item for item in results if (item.get("total_reviews") or 0) >= min_reviews]
        qualified.sort(key=lambda item: item.get("total_reviews") or 0, reverse=True)
        best_businesses = [
            {
                "name": item.get("name"),
                "reviews": item.get("total_reviews") or 0,
                "address": item.get("address"),
            }
            for item in qualified[:3]
        ]
        best_reviews = best_businesses[0]["reviews"] if best_businesses else 0
        score = (len(qualified) * 1000) + best_reviews
        city_rows.append({
            "city": city,
            "qualified_count": len(qualified),
            "best_reviews": best_reviews,
            "best_businesses": best_businesses,
            "sampled": len(results),
            "score": score,
        })

    city_rows.sort(key=lambda item: item.get("score", 0), reverse=True)
    top_cities = city_rows[:5]
    summary_parts = []
    for row in top_cities[:3]:
        if row.get("qualified_count", 0) > 0:
            summary_parts.append(f"{row['city']} ({row['qualified_count']} leads com +{min_reviews} reviews)")
        elif row.get("sampled", 0) > 0:
            summary_parts.append(f"{row['city']} ({row['sampled']} candidatos encontrados)")

    country = context.get("region") or "região selecionada"
    snapshot = {
        "available": True,
        "country": country,
        "query": query,
        "min_reviews": min_reviews,
        "cities_tested": len(cities),
        "top_cities": top_cities,
        "summary": (
            f"Google Places analisado para {country}. "
            + ("Top inicial: " + ", ".join(summary_parts) + "." if summary_parts else "Não encontrei volume útil nas cidades testadas.")
        ),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _CACHE[cache_key] = (time.time(), snapshot)
    return snapshot
