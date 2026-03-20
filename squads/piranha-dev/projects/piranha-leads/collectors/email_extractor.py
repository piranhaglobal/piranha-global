import re
import requests
from bs4 import BeautifulSoup
from config import EMAIL_TIMEOUT

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

CONTACT_PAGE_SLUGS = [
    "/contacto", "/contact", "/contactanos",
    "/sobre-nosotros", "/about", "/info",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

IGNORED_EMAIL_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "domain.com",
    "squarespace.com", "wordpress.com", "shopify.com",
}


def extract_email_from_website(url: str, use_firecrawl_fallback: bool = True) -> str | None:
    """
    Tries to find an email address from a website.
    Strategy:
      1. Scrape homepage with simple requests
      2. Try common contact page slugs
      3. Fallback to Firecrawl for JS-heavy sites
    """
    if not url:
        return None

    base_url = url.rstrip("/")

    # 1. Try homepage (simple)
    html = _fetch_simple(base_url)
    if html:
        email = _find_email_in_html(html)
        if email:
            return email

    # 2. Try contact pages (simple)
    for slug in CONTACT_PAGE_SLUGS:
        html = _fetch_simple(base_url + slug)
        if html:
            email = _find_email_in_html(html)
            if email:
                return email

    # 3. Firecrawl fallback for JS-heavy sites
    if use_firecrawl_fallback:
        from collectors.firecrawl_extractor import fetch_with_firecrawl, firecrawl_available
        if firecrawl_available():
            print(f"  ↳ Firecrawl fallback para {url}")
            html = fetch_with_firecrawl(base_url)
            if html:
                email = _find_email_in_html(html)
                if email:
                    return email

    return None


def _fetch_simple(url: str) -> str | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=EMAIL_TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None


def _find_email_in_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")

    # Priority: mailto: links — most reliable
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if _is_valid_email(email):
                return email

    # Fallback: regex scan
    for email in EMAIL_REGEX.findall(html):
        if _is_valid_email(email):
            return email

    return None


def _is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower()
    if domain in IGNORED_EMAIL_DOMAINS:
        return False
    if any(email.endswith(ext) for ext in (".png", ".jpg", ".gif", ".svg", ".webp")):
        return False
    return True
