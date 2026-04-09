"""Cliente Shopify — busca checkouts abandonados do 8º dia."""

import re
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
            or shipping.get("phone")
            or ""
        ).strip()

        products = []
        for item in checkout.get("line_items", []):
            product_id = item.get("product_id")
            product_info = self._get_product_info(product_id) if product_id else {
                "description": "", "url": "", "product_details": "", "faqs": [],
            }
            products.append({
                "title": item.get("title", ""),
                "vendor": item.get("vendor", ""),
                "price": item.get("price", ""),
                "url": product_info["url"],
                "description": product_info["description"],
                "product_details": product_info.get("product_details", ""),
                "faqs": product_info.get("faqs", []),
            })

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
            "subtotal_price": checkout.get("subtotal_price", ""),
            "shipping_lines": checkout.get("shipping_lines", []),
            "total_tax": checkout.get("total_tax", ""),
            "created_at": checkout.get("created_at", ""),
        }

    def _get_product_info(self, product_id: int | str, max_chars: int = 400) -> dict:
        """
        Busca descrição, detalhes e FAQs de um produto Shopify pelo seu ID.
        Args:
            product_id: ID do produto Shopify
            max_chars: número máximo de caracteres da descrição principal
        Returns:
            dict com "description", "product_details", "faqs" (list[dict]) e "url"
        """
        try:
            data = self._make_request("GET", f"/products/{product_id}.json")
            product = data.get("product", {})
            body_html = product.get("body_html", "") or ""
            handle = product.get("handle", "") or ""
            # Usar domínio público da loja para URLs (FAQs/scraping)
            # SHOPIFY_STOREFRONT_URL tem prioridade; fallback: derivar do myshopify handle
            storefront = (
                Config.SHOPIFY_STOREFRONT_URL.strip().rstrip("/")
                or "https://" + Config.SHOPIFY_STORE_URL.replace(".myshopify.com", ".com").split("/")[0]
            )
            if not storefront.startswith("http"):
                storefront = "https://" + storefront
            url = f"{storefront}/products/{handle}" if handle else ""

            product_details = self._get_product_details_metafield(product_id)
            faqs = self._get_product_faqs(url) if url else []

            return {
                "description": self._clean_html(body_html, max_chars),
                "product_details": product_details,
                "faqs": faqs,
                "url": url,
            }
        except Exception as e:
            logger.warning(f"Não foi possível obter informação do produto {product_id}: {e}")
            return {"description": "", "product_details": "", "faqs": [], "url": ""}

    def _get_product_details_metafield(self, product_id: int | str, max_chars: int = 600) -> str:
        """
        Busca o metafield info.longdescription de um produto (features/especificações).
        Args:
            product_id: ID do produto Shopify
            max_chars: limite de caracteres do texto extraído
        Returns:
            texto limpo das especificações, ou "" se não disponível
        """
        try:
            data = self._make_request(
                "GET", f"/products/{product_id}/metafields.json",
                params={"namespace": "info", "key": "longdescription"},
            )
            metafields = data.get("metafields", [])
            if not metafields:
                return ""
            raw = metafields[0].get("value", "") or ""
            return self._clean_html(raw, max_chars)
        except Exception as e:
            logger.warning(f"Não foi possível obter metafield longdescription do produto {product_id}: {e}")
            return ""

    def _get_product_faqs(self, product_url: str, max_faqs: int = 20) -> list[dict]:
        """
        Extrai FAQs da página pública do produto (divs com class 'question').
        Remove duplicados (o tema renderiza blocos mobile + desktop).
        Args:
            product_url: URL completa do produto na loja
            max_faqs: número máximo de FAQs únicas a retornar
        Returns:
            lista de dicts com "question" e "answer", sem duplicados
        """
        try:
            resp = self.session.get(
                product_url,
                headers={"Accept": "text/html"},
                timeout=10,
            )
            resp.raise_for_status()
            html = resp.text

            # Cada FAQ está num div.question: texto direto = pergunta, div.metafield-rich_text_field = resposta
            faq_blocks = re.findall(
                r'class="[^"]*question[^"]*"[^>]*>\s*(.*?)\s*<div class="metafield-rich_text_field">(.*?)</div>',
                html,
                re.DOTALL,
            )
            faqs: list[dict] = []
            seen_questions: set[str] = set()
            for question_raw, answer_raw in faq_blocks:
                question = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", question_raw)).strip()
                answer = self._clean_html(answer_raw, 400)
                if question and answer and question not in seen_questions:
                    seen_questions.add(question)
                    faqs.append({"question": question, "answer": answer})
                if len(faqs) >= max_faqs:
                    break

            logger.info(f"FAQs extraídas para {product_url}: {len(faqs)} únicas")
            return faqs
        except Exception as e:
            logger.warning(f"Não foi possível extrair FAQs de {product_url}: {e}")
            return []

    @staticmethod
    def _clean_html(html: str, max_chars: int = 400) -> str:
        """Remove tags HTML e normaliza espaços para uso em prompt de voz."""
        if not html:
            return ""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + "..."
        return text

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
