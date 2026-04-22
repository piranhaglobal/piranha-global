"""
Layer 4: Search-based email discovery via Serper.dev (Google Search API).
Strategy: search '"Business Name" "City" "email"' and extract from snippets.
"""
import os
import re
import unicodedata
from urllib.parse import urlparse

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
_SOCIAL_HOSTS = {
    "instagram.com", "www.instagram.com",
    "facebook.com", "www.facebook.com",
}
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


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


def _clean_link(url: str | None) -> str | None:
    if not url:
        return None
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        return None
    return cleaned


def _host(url: str | None) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _normalize_phone_candidate(raw_phone: str) -> str | None:
    phone = raw_phone.strip()
    phone = re.sub(r"(?:ext|ramal|anexo)\s*\d+$", "", phone, flags=re.IGNORECASE).strip()
    phone = re.sub(r"[^\d+]", "", phone)
    if not phone:
        return None
    if not phone.startswith("+"):
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 9:
            phone = f"+34{digits}"
        else:
            return None

    try:
        from validators.contact_validator import validate_phone
        return phone if validate_phone(phone)["valid"] else None
    except Exception:
        return None


def _phones_from_results(results: list[dict]) -> list[str]:
    found: list[str] = []
    for result in results:
        text = " ".join(
            part for part in (
                result.get("title", ""),
                result.get("snippet", ""),
                result.get("link", ""),
            ) if part
        )
        for raw_phone in _PHONE_RE.findall(text):
            phone = _normalize_phone_candidate(raw_phone)
            if phone and phone not in found:
                found.append(phone)
    return found


def _pick_best_website(results: list[dict]) -> str | None:
    for result in results:
        link = _clean_link(result.get("link"))
        host = _host(link)
        if not link or not host:
            continue
        if host in _SOCIAL_HOSTS:
            continue
        if any(host == noise or host.endswith("." + noise) for noise in _NOISE_DOMAINS):
            continue
        return link
    return None


def _pick_social_link(results: list[dict], host_suffix: str) -> str | None:
    for result in results:
        link = _clean_link(result.get("link"))
        host = _host(link)
        if host == host_suffix or host == f"www.{host_suffix}":
            return link
    return None


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


def search_contact_info_for_lead(name: str, city: str) -> dict:
    """
    Search-based enrichment for missing contact information.
    Returns any combination of email, phone, website and social links.
    """
    if not name:
        return {
            "email": None,
            "phone": None,
            "website": None,
            "instagram_url": None,
            "facebook_url": None,
        }

    generic_results = _search_serper(f'"{name}" "{city}"', num=5)
    contact_results = _search_serper(f'"{name}" "{city}" contacto OR contact OR telefono OR phone OR email', num=5)
    instagram_results = _search_serper(f'"{name}" "{city}" site:instagram.com', num=5)
    facebook_results = _search_serper(f'"{name}" "{city}" site:facebook.com', num=5)

    combined_results = generic_results + contact_results + instagram_results + facebook_results
    emails = _emails_from_results(combined_results, name, city)
    phones = _phones_from_results(combined_results)

    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "website": _pick_best_website(generic_results + contact_results),
        "instagram_url": _pick_social_link(instagram_results + generic_results, "instagram.com"),
        "facebook_url": _pick_social_link(facebook_results + generic_results, "facebook.com"),
    }
