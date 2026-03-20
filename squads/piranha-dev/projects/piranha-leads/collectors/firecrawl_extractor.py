import os
import requests


def fetch_with_firecrawl(url: str, wait_for: int = 3000, timeout: int = 15000) -> str | None:
    """
    Envia URL para o Firecrawl local e retorna o HTML renderizado.
    Útil para sites com JavaScript pesado que o requests simples não consegue processar.
    """
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
        content = data.get("data", {}).get("content") or data.get("content")
        return content
    except Exception as e:
        print(f"  [Firecrawl] Erro ao processar {url}: {e}")
        return None


def firecrawl_available() -> bool:
    """Verifica se o Firecrawl está rodando localmente."""
    api_url = os.getenv("FIRECRAWL_API_URL", "http://localhost:3002")
    try:
        resp = requests.get(f"{api_url}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
