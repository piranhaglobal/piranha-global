"""Cliente Shopify — busca checkouts abandonados do 8º dia."""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Prefixos internacionais → country code ISO 3166-1 (apenas UE + países relevantes)
# Ordenados do mais específico (mais dígitos) para o menos específico
_PHONE_PREFIX_MAP: list[tuple[str, str]] = [
    ("+358", "FI"), ("+353", "IE"), ("+352", "LU"), ("+359", "BG"),
    ("+357", "CY"), ("+356", "MT"), ("+385", "HR"), ("+386", "SI"),
    ("+370", "LT"), ("+371", "LV"), ("+372", "EE"), ("+420", "CZ"),
    ("+421", "SK"), ("+351", "PT"), ("+354", "IS"),
    ("+34",  "ES"), ("+33",  "FR"), ("+49",  "DE"), ("+39",  "IT"),
    ("+31",  "NL"), ("+32",  "BE"), ("+48",  "PL"), ("+46",  "SE"),
    ("+45",  "DK"), ("+43",  "AT"), ("+36",  "HU"), ("+40",  "RO"),
    ("+30",  "GR"), ("+44",  "GB"),
]


def _infer_country_from_phone(phone: str) -> str:
    """Infere o country code ISO a partir do prefixo internacional do número."""
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    if not digits.startswith("+"):
        return ""
    for prefix, country in _PHONE_PREFIX_MAP:
        if digits.startswith(prefix):
            return country
    return ""


class ShopifyClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self) -> None:
        """Inicializa sessão HTTP com headers de autenticação Shopify."""
        self.base_url = (
            f"https://{Config.SHOPIFY_STORE_URL}/admin/api/{Config.SHOPIFY_API_VERSION}"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": Config.SHOPIFY_ACCESS_TOKEN,
            "Content-Type": "application/json",
        })

    def get_abandoned_checkouts(
        self,
        day_min: int = 8,
        day_max: int = 7,
    ) -> list[dict]:
        """
        Busca checkouts criados entre day_min e day_max dias atrás,
        não convertidos (completed_at=null) e com telefone.
        Args:
            day_min: limite superior da janela em dias (default 8)
            day_max: limite inferior da janela em dias (default 7)
        Returns:
            lista de dicts normalizados prontos para o CallHandler
        Raises:
            requests.HTTPError: em caso de falha na API
        """
        now = datetime.now(timezone.utc)
        created_at_min = (now - timedelta(days=day_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
        created_at_max = (now - timedelta(days=day_max)).strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"A buscar checkouts entre {created_at_min} e {created_at_max}")

        raw = self._make_request("GET", "/checkouts.json", params={
            "created_at_min": created_at_min,
            "created_at_max": created_at_max,
            "status": "open",
            "limit": 250,
        })

        checkouts = raw.get("checkouts", [])
        logger.info(f"{len(checkouts)} checkouts encontrados na janela de tempo")

        eligible = [
            self._extract_contact(c)
            for c in checkouts
            if self._is_eligible(c)
        ]
        logger.info(f"{len(eligible)} checkouts elegíveis para ligação")
        return eligible

    def _is_eligible(self, checkout: dict) -> bool:
        """
        Verifica se o checkout é elegível para ligação.
        Critérios: completed_at é null e tem phone.
        Args:
            checkout: dict bruto da Shopify
        Returns:
            True se elegível
        """
        if checkout.get("completed_at") is not None:
            return False
        phone = checkout.get("phone") or checkout.get("customer", {}).get("phone", "")
        return bool(phone and phone.strip())

    def _extract_contact(self, checkout: dict) -> dict:
        """
        Extrai e normaliza os campos necessários do checkout.
        Args:
            checkout: dict bruto da Shopify
        Returns:
            dict com: id, phone, name, country_code, products, total_price
        """
        customer = checkout.get("customer") or {}
        shipping = checkout.get("shipping_address") or checkout.get("billing_address") or {}

        phone = (
            checkout.get("phone")
            or customer.get("phone")
            or ""
        ).strip()

        products = [
            {
                "title": item.get("title", ""),
                "vendor": item.get("vendor", ""),
                "price": item.get("price", ""),
            }
            for item in checkout.get("line_items", [])
        ]

        country_code = (
            shipping.get("country_code")
            or _infer_country_from_phone(phone)
            or "PT"
        ).upper()

        return {
            "id": str(checkout.get("id", "")),
            "phone": phone,
            "name": customer.get("first_name") or "cliente",
            "country_code": country_code,
            "products": products,
            "total_price": checkout.get("total_price", ""),
            "created_at": checkout.get("created_at", ""),
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict:
        """
        Faz requisição HTTP com retry e backoff exponencial.
        Args:
            method: "GET", "POST", etc.
            endpoint: caminho relativo ao base_url
        Returns:
            dict com resposta JSON
        Raises:
            requests.HTTPError: após esgotar retries
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                logger.debug(f"Shopify {method} {endpoint} → {response.status_code}")
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limit Shopify. A aguardar {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"Erro HTTP Shopify: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro de rede Shopify (tentativa {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise

        return {}
