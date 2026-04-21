"""
Layer 4: Search-based email discovery via Serper.dev (Google Search API).
Strategy: search '"Business Name" "City" "email"' and extract from snippets.
"""
import os
import re
import unicodedata

import requests

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}(?=[^a-zA-Z]|$)",
    re.IGNORECASE,
)

# Domains that never belong to a business contact
_NOISE_DOMAINS = {
    "wix.com", "wixsite.com", "wordpress.com", "squarespace.com",
    "shopify.com", "mailchimp.com", "example.com", "sentry.io",
    "w3.org", "schema.org", "google.com", "googleapis.com",
    "adobe.com", "cloudflare.com", "jquery.com",
    "facebook.com", "instagram.com", "twitter.com", "tiktok.com",
    "divi.express", "elegantthemes.com", "themeforest.net",
    "crazybuyboxes.com", "noreply.com", "email.com",
    # Booking / SaaS platforms
    "fresha.com", "treatwell.com", "booksy.com", "vagaro.com",
    "mindbodyonline.com", "glofox.com", "timely.com",
    # Website builders
    "webador.es", "webador.com", "jimdo.com", "weebly.com",
    # Known retail/unrelated
    "casadellibro.com", "elcorteingles.es", "fnac.es",
}

# Only accept these TLDs — rejects malformed captures like .wu, .co.wu, etc.
_VALID_TLDS = {
    "com", "es", "org", "net", "eu", "cat", "gal", "eus",
    "pt", "fr", "de", "uk", "it", "nl", "be", "io", "co",
    "info", "biz", "me", "email", "store", "online", "art",
    "ink", "tattoo", "studio", "design", "gallery", "shop",
}

# Free/personal providers — valid only when the email local part looks like a business
_PERSONAL_PROVIDERS = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "icloud.com"}


def _normalize(text: str) -> str:
    """Lowercase, strip accents and non-alphanumerics."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_str)


def _is_valid_email(email: str, name: str = "", city: str = "") -> bool:
    """Returns True if the email is a real business contact related to the business."""
    domain = email.split("@")[-1].lower()
    local = email.split("@")[0].lower()

    if any(domain == p or domain.endswith("." + p) for p in _NOISE_DOMAINS):
        return False

    # Reject emails with unknown TLD
    tld = domain.rsplit(".", 1)[-1]
    if tld not in _VALID_TLDS:
        return False

    # Generic industry words that appear in many businesses — not useful as identifiers
    _GENERIC_WORDS = {"tattoo", "tatto", "tatuaje", "tatuajes", "piercing", "studio",
                      "estudio", "estudi", "salon", "shop", "arte", "artistas", "fine",
                      "line", "lines", "collective", "community"}

    # Keywords ONLY from business name (not city) — city is too generic
    name_keywords = [
        _normalize(w) for w in re.split(r"\s+", name)
        if len(w) >= 3 and _normalize(w) not in _GENERIC_WORDS
    ]
    keywords = name_keywords

    if not keywords:
        return False  # sem keywords identificáveis, não é possível validar

    # Flatten the email into a searchable string: "info@ritualtattoo.es" → "inforitualtattooaes"
    email_flat = _normalize(email.replace("@", " ").replace(".", " ").replace("-", " ").replace("_", " "))

    # Accept if any keyword appears anywhere in the email address
    return any(kw in email_flat for kw in keywords)


def _search_serper(query: str, num: int = 5) -> list[dict]:
    """Calls Serper.dev Google Search API and returns organic results."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "es", "hl": "es", "num": num},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("organic", [])
    except Exception:
        return []


def _emails_from_results(results: list[dict], name: str = "", city: str = "") -> list[str]:
    """Extracts valid emails from Serper result snippets."""
    found = []
    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}"
        for email in _EMAIL_RE.findall(text):
            if _is_valid_email(email, name, city) and email not in found:
                found.append(email)
    return found


def search_email_for_lead(name: str, city: str) -> str | None:
    """
    Searches Google (via Serper) for the business email using advanced queries.
    Returns the first valid email found in snippets, or None.

    Queries tried (in order):
    1. '"Name" "City" "email"'          — email in snippet (most reliable)
    2. '"Name" "City" email contacto'   — broader terms
    3. '"Name" "City" site:facebook.com'— Facebook page snippet
    4. '"Name" "City" site:instagram.com' — Instagram snippet
    """
    if not name:
        return None

    queries = [
        f'"{name}" "{city}" "email"',
        f'"{name}" "{city}" email contacto',
        f'"{name}" "{city}" site:facebook.com',
        f'"{name}" "{city}" site:instagram.com',
    ]

    for query in queries:
        results = _search_serper(query, num=5)
        emails = _emails_from_results(results, name, city)
        if emails:
            return emails[0]

    return None
