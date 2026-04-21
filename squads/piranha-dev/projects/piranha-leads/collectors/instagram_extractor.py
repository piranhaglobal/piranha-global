import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Padrões para extrair handle do Instagram a partir de um website
_IG_HANDLE_PATTERNS = [
    re.compile(r'instagram\.com/([A-Za-z0-9_.]{1,30})/?["\'>\s]'),
    re.compile(r'instagram\.com/([A-Za-z0-9_.]{1,30})$'),
]

IGNORED_EMAIL_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "domain.com",
    "squarespace.com", "wordpress.com", "shopify.com",
    "instagram.com", "facebook.com", "google.com",
    "w3.org", "schema.org",
}

# Handles genéricos do Instagram que não pertencem ao negócio
_IGNORED_HANDLES = {
    "instagram", "p", "reel", "reels", "stories", "explore",
    "accounts", "login", "signup", "about", "legal", "privacy",
    "help", "press", "api", "blog", "jobs", "directory",
}


def extract_email_from_instagram(website_url: str) -> str | None:
    """
    1. Encontra o handle do Instagram no website do studio.
    2. Acede à página pública do Instagram.
    3. Extrai o email da bio ou dos links de contacto.
    """
    if not website_url:
        return None

    handle = _find_instagram_handle(website_url)
    if not handle:
        return None

    return _scrape_instagram_bio_email(handle)


def _find_instagram_handle(url: str) -> str | None:
    """Extrai o handle do Instagram a partir do HTML do website."""
    try:
        resp = requests.get(
            url.rstrip("/"),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=8,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    for pattern in _IG_HANDLE_PATTERNS:
        for match in pattern.finditer(html):
            handle = match.group(1).rstrip("/").strip()
            if handle and handle.lower() not in _IGNORED_HANDLES and len(handle) >= 2:
                return handle

    return None


def _scrape_instagram_bio_email(handle: str) -> str | None:
    """
    Acede à página pública do Instagram (mobile UA) e extrai email da bio.
    O Instagram mobile devolve JSON com a bio em alguns casos,
    ou podemos fazer regex directamente no HTML.
    """
    url = f"https://www.instagram.com/{handle}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    # Estratégia 1: procurar email nos dados JSON embebidos (window._sharedData ou script tags)
    # O Instagram embebe dados do perfil em <script type="application/ld+json">
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.get_text()
        if "@" in text:
            for email in EMAIL_REGEX.findall(text):
                if _is_valid(email):
                    print(f"  ↳ Instagram [{handle}] email em ld+json: {email}")
                    return email

    # Estratégia 2: regex no HTML completo (bio aparece como string JSON)
    # Bio costuma aparecer como "biography":"..."
    bio_match = re.search(r'"biography"\s*:\s*"([^"]{0,300})"', html)
    if bio_match:
        bio_text = bio_match.group(1)
        # Decode unicode escapes comuns (\u0040 = @)
        bio_text = bio_text.encode("utf-8").decode("unicode_escape", errors="ignore")
        bio_text = bio_text.replace(r"\u0040", "@").replace(r"\u002e", ".")
        for email in EMAIL_REGEX.findall(bio_text):
            if _is_valid(email):
                print(f"  ↳ Instagram [{handle}] email na bio: {email}")
                return email

    # Estratégia 3: regex geral no HTML (último recurso)
    for email in EMAIL_REGEX.findall(html):
        if _is_valid(email):
            print(f"  ↳ Instagram [{handle}] email no HTML: {email}")
            return email

    return None


def _is_valid(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].lower()
    if domain in IGNORED_EMAIL_DOMAINS:
        return False
    if any(email.lower().endswith(ext) for ext in (".png", ".jpg", ".gif", ".svg", ".webp")):
        return False
    local = email.split("@")[0]
    if len(local) < 2 or len(domain) < 4:
        return False
    return True
