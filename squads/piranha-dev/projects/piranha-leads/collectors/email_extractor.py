import re
import requests
from bs4 import BeautifulSoup
from config import EMAIL_TIMEOUT

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Slugs cobrindo ES, PT, FR, IT, DE, GB, NL, BE, PL, etc.
CONTACT_PAGE_SLUGS = [
    # Espanhol
    "/contacto", "/contactanos", "/sobre-nosotros", "/aviso-legal",
    # Português
    "/contacto", "/contato", "/contactos", "/sobre-nos", "/fale-connosco",
    # Inglês
    "/contact", "/contact-us", "/about", "/about-us", "/info",
    # Francês
    "/contact", "/nous-contacter", "/a-propos",
    # Alemão / Austríaco
    "/impressum", "/kontakt", "/datenschutz", "/ueber-uns",
    # Italiano
    "/contatti", "/chi-siamo",
    # Neerlandês
    "/contact", "/over-ons",
    # Polaco
    "/kontakt",
    # Genérico
    "/legal", "/privacy", "/team",
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
    "instagram.com", "facebook.com", "google.com",
    "w3.org", "schema.org", "apple.com", "microsoft.com",
}

# Padrões de obfuscação comuns
_OBFUSCATION_PATTERNS = [
    # info[at]studio.com  /  info [at] studio.com
    (re.compile(r"([a-zA-Z0-9._%+\-]+)\s*[\[\(]at[\]\)]\s*([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I), r"\1@\2"),
    # info AT studio DOT com
    (re.compile(r"([a-zA-Z0-9._%+\-]+)\s+AT\s+([a-zA-Z0-9.\-]+)\s+DOT\s+([a-zA-Z]{2,})", re.I), r"\1@\2.\3"),
    # info(arroba)studio.es
    (re.compile(r"([a-zA-Z0-9._%+\-]+)\(arroba\)([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I), r"\1@\2"),
    # info{at}studio.com
    (re.compile(r"([a-zA-Z0-9._%+\-]+)\{at\}([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I), r"\1@\2"),
    # info _at_ studio.com
    (re.compile(r"([a-zA-Z0-9._%+\-]+)\s+_at_\s+([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.I), r"\1@\2"),
]


def extract_email_from_website(url: str, use_firecrawl_fallback: bool = True) -> str | None:
    if not url:
        return None

    base_url = url.rstrip("/")

    # 1. Homepage simples
    html = _fetch_simple(base_url)
    if html:
        email = _find_email_in_html(html)
        if email:
            return email

    # 2. Páginas de contacto (sem duplicados, preservando ordem)
    seen_slugs: set[str] = set()
    for slug in CONTACT_PAGE_SLUGS:
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        html = _fetch_simple(base_url + slug)
        if html:
            email = _find_email_in_html(html)
            if email:
                return email

    # 3. Firecrawl Spider — crawl do site inteiro (até 5 páginas)
    if use_firecrawl_fallback:
        from collectors.firecrawl_extractor import spider_for_email, firecrawl_available
        if firecrawl_available():
            print(f"  ↳ Firecrawl Spider para {base_url}")
            email = spider_for_email(base_url, max_pages=5)
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

    # 1. mailto: links — mais fiável
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if _is_valid_email(email):
                return email

    # 2. Meta tags (og:email, author, contact)
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        content = meta.get("content") or ""
        if name in ("og:email", "email", "author", "contact") and "@" in content:
            if _is_valid_email(content.strip()):
                return content.strip()

    # 3. Desobfuscação no texto visível
    text = soup.get_text(" ")
    email = _deobfuscate_email(text)
    if email:
        return email

    # 4. Regex scan no HTML completo
    for email in EMAIL_REGEX.findall(html):
        if _is_valid_email(email):
            return email

    return None


def _deobfuscate_email(text: str) -> str | None:
    for pattern, replacement in _OBFUSCATION_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = pattern.sub(replacement, match.group(0))
            if _is_valid_email(candidate):
                return candidate
    return None


def _is_valid_email(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower()
    if domain in IGNORED_EMAIL_DOMAINS:
        return False
    if any(email.lower().endswith(ext) for ext in (".png", ".jpg", ".gif", ".svg", ".webp")):
        return False
    # Rejeitar strings muito curtas ou claramente inválidas
    local = email.split("@")[0]
    if len(local) < 2 or len(domain) < 4:
        return False
    return True
