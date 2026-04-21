import os
import re
import requests
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

IGNORED_EMAIL_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "domain.com",
    "squarespace.com", "wordpress.com", "shopify.com",
    "instagram.com", "facebook.com", "google.com",
    "w3.org", "schema.org",
}


def fetch_with_firecrawl(url: str, wait_for: int = 3000, timeout: int = 15000) -> str | None:
    """Renderiza uma página via Firecrawl e devolve o HTML."""
    api_url = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
    payload = {
        "url": url,
        "formats": ["html"],
        "onlyMainContent": True,
        "waitFor": wait_for,
        "timeout": timeout,
    }
    try:
        resp = requests.post(f"{api_url}/v1/scrape", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("content") or data.get("content")
    except Exception as e:
        print(f"  [Firecrawl] Erro ao processar {url}: {e}")
        return None


def spider_for_email(base_url: str, max_pages: int = 5) -> str | None:
    """
    Faz crawl do site inteiro via Firecrawl (até max_pages páginas)
    e procura um email em todo o conteúdo encontrado.
    Prioriza páginas de contacto antes de páginas genéricas.
    """
    api_url = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")

    payload = {
        "url": base_url,
        "limit": max_pages,
        "scrapeOptions": {
            "formats": ["html"],
            "onlyMainContent": False,
        },
        # Prioriza páginas de contacto
        "includePaths": [
            "*contact*", "*contacto*", "*contato*", "*impressum*",
            "*about*", "*sobre*", "*info*", "*legal*",
        ],
    }

    try:
        resp = requests.post(f"{api_url}/v1/crawl", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [Firecrawl Spider] Erro em {base_url}: {e}")
        return None

    # Suporte a resposta síncrona e assíncrona do Firecrawl
    pages = []
    if isinstance(data.get("data"), list):
        pages = data["data"]
    elif data.get("status") == "completed" and isinstance(data.get("data"), list):
        pages = data["data"]

    for page in pages:
        html = page.get("content") or page.get("html") or ""
        if not html:
            continue
        email = _extract_email_from_html(html)
        if email:
            return email

    return None


def firecrawl_available() -> bool:
    """Verifica se o Firecrawl está a correr localmente."""
    api_url = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
    try:
        resp = requests.get(f"{api_url}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _extract_email_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")

    # mailto: primeiro
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if _is_valid(email):
                return email

    # regex scan
    for email in EMAIL_REGEX.findall(html):
        if _is_valid(email):
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
    return True
