import os
import time
import requests
from config import SEARCH_QUERY, RESULTS_PER_CITY, REQUEST_DELAY, MIN_REVIEWS


PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def search_studios_in_city(city: str, api_key: str, query: str | None = None) -> list[dict]:
    """
    Searches for tattoo studios in a given city using Google Places Text Search.
    Handles pagination to collect up to RESULTS_PER_CITY results.
    """
    studios = []
    search_query = f"{query or SEARCH_QUERY} en {city}, España"
    params = {
        "query": search_query,
        "key": api_key,
        "language": "es",
        "region": "es",
    }

    # Fetch up to RESULTS_PER_CITY candidates (max 60 = 3 pages of 20)
    # The caller is responsible for filtering by MIN_REVIEWS
    while len(studios) < RESULTS_PER_CITY:
        response = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            print(f"  [!] Places API error for {city}: {data.get('status')} — {data.get('error_message', '')}")
            break

        results = data.get("results", [])
        for place in results:
            studio = _parse_place(place, city)
            studios.append(studio)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        if len(studios) >= RESULTS_PER_CITY:
            break

        # Google requires a short delay before using next_page_token
        time.sleep(2)
        params = {"pagetoken": next_page_token, "key": api_key}

    return studios


def get_place_details(place_id: str, api_key: str) -> dict:
    """
    Fetches additional details for a place (website, formatted phone).
    """
    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number,international_phone_number",
        "key": api_key,
        "language": "es",
    }
    response = requests.get(PLACES_DETAILS_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        return {}

    result = data.get("result", {})
    return {
        "website": result.get("website"),
        "phone": result.get("international_phone_number") or result.get("formatted_phone_number"),
    }


def _parse_place(place: dict, city: str) -> dict:
    return {
        "place_id": place.get("place_id"),
        "name": place.get("name"),
        "city": city,
        "address": place.get("formatted_address"),
        "phone": None,       # filled in by get_place_details
        "website": None,     # filled in by get_place_details
        "email": None,       # filled in by email_extractor
        "rating": place.get("rating"),
        "total_reviews": place.get("user_ratings_total"),
        "business_status": place.get("business_status"),  # OPERATIONAL, CLOSED_TEMPORARILY, etc.
    }
