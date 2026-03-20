"""Cliente Shopify — pedidos do dia 25 e cache de consumíveis."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

CACHE_FILE = Path(__file__).parent.parent.parent / "cache" / "consumables.json"


class ShopifyClient:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self) -> None:
        """Inicializa sessão HTTP com headers de autenticação Shopify."""
        self.base_url = (
            f"https://{Config.SHOPIFY_STORE_URL}"
            f"/admin/api/{Config.SHOPIFY_API_VERSION}"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": Config.SHOPIFY_ACCESS_TOKEN,
            "Content-Type": "application/json",
        })

    def get_orders_day_25(self) -> list[dict]:
        """
        Busca pedidos pagos criados entre 24 e 26 dias atrás (janela do dia 25).
        Returns:
            lista de dicts normalizados prontos para o MessageHandler
        Raises:
            requests.HTTPError: falha na API
        """
        now = datetime.now(timezone.utc)
        created_at_min = (now - timedelta(days=26)).strftime("%Y-%m-%dT%H:%M:%SZ")
        created_at_max = (now - timedelta(days=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"A buscar pedidos entre {created_at_min} e {created_at_max}")

        raw = self._make_request("GET", "/orders.json", params={
            "created_at_min": created_at_min,
            "created_at_max": created_at_max,
            "financial_status": "paid",
            "status": "any",
            "limit": 250,
        })

        orders = raw.get("orders", [])
        logger.info(f"{len(orders)} pedidos encontrados na janela do dia 25")

        normalized = [self._extract_order(o) for o in orders]
        return normalized

    def get_consumable_ids(self, force_refresh: bool = False) -> set[int]:
        """
        Retorna set de product_ids da colecção consumables-and-hygiene.
        Usa cache local se existir e for do dia de hoje.
        Args:
            force_refresh: ignorar cache e refazer fetch
        Returns:
            set de integers com os product_ids consumíveis
        """
        if not force_refresh and self._is_cache_valid():
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            ids = set(data.get("product_ids", []))
            logger.info(f"Cache de consumíveis carregado: {len(ids)} produtos")
            return ids

        logger.info("A actualizar cache de consumíveis...")
        collection_id = self._fetch_collection_id()

        if not collection_id:
            logger.error("Colecção consumables-and-hygiene não encontrada na Shopify")
            return set()

        ids = self._fetch_product_ids(collection_id)
        logger.info(f"{len(ids)} produtos consumíveis encontrados")

        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps({
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "collection_id": collection_id,
                "product_ids": list(ids),
            }, indent=2),
            encoding="utf-8",
        )

        return ids

    def _fetch_collection_id(self) -> int | None:
        """
        Busca o ID da colecção pelo handle.
        Tenta custom_collections primeiro, depois smart_collections.
        Returns:
            integer do collection_id ou None se não encontrar
        """
        handle = Config.SHOPIFY_CONSUMABLES_HANDLE

        for endpoint in (
            f"/custom_collections.json?handle={handle}",
            f"/smart_collections.json?handle={handle}",
        ):
            try:
                data = self._make_request("GET", endpoint.split("?")[0],
                                          params={"handle": handle})
                key = "custom_collections" if "custom" in endpoint else "smart_collections"
                collections = data.get(key, [])
                if collections:
                    cid = collections[0]["id"]
                    logger.info(f"Colecção encontrada ({key}): id={cid}")
                    return cid
            except Exception as e:
                logger.warning(f"Erro ao buscar {endpoint}: {e}")

        return None

    def _fetch_product_ids(self, collection_id: int) -> set[int]:
        """
        Busca todos os product_ids de uma colecção via /collects.json.
        Trata paginação com limit=250.
        Args:
            collection_id: ID da colecção Shopify
        Returns:
            set de product_ids
        """
        ids: set[int] = set()
        page_info = None

        while True:
            params: dict[str, Any] = {
                "collection_id": collection_id,
                "limit": 250,
            }
            if page_info:
                params["page_info"] = page_info

            data, headers = self._make_request_with_headers("GET", "/collects.json", params=params)
            collects = data.get("collects", [])
            ids.update(c["product_id"] for c in collects)

            # Paginação via Link header da mesma resposta (sem segunda requisição)
            link = headers.get("Link", "")
            if 'rel="next"' not in link:
                break

            page_info = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    page_info = part.split("page_info=")[1].split(">")[0]
                    break

            if not page_info:
                break

        return ids

    def _extract_order(self, order: dict) -> dict:
        """
        Normaliza campos relevantes de um pedido bruto da Shopify.
        Args:
            order: dict bruto da API
        Returns:
            dict com: id, phone, name, country_code,
                      line_items: [{product_id, title}]
        """
        customer = order.get("customer") or {}
        shipping = order.get("shipping_address") or order.get("billing_address") or {}

        phone = (
            order.get("phone")
            or customer.get("phone")
            or ""
        ).strip()

        line_items = [
            {
                "product_id": item.get("product_id"),
                "title": item.get("title", ""),
            }
            for item in order.get("line_items", [])
        ]

        return {
            "id": str(order.get("id", "")),
            "phone": phone,
            "name": customer.get("first_name") or "cliente",
            "country_code": (shipping.get("country_code") or "PT").upper(),
            "line_items": line_items,
        }

    def _is_cache_valid(self) -> bool:
        """
        Verifica se o cache existe e foi criado hoje.
        Returns:
            True se cache válido
        """
        if not CACHE_FILE.exists():
            return False
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return data.get("date") == datetime.utcnow().strftime("%Y-%m-%d")
        except Exception:
            return False

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict:
        """
        Requisição HTTP com retry e backoff exponencial.
        Trata HTTP 429 com espera proporcional.
        """
        body, _ = self._make_request_with_headers(method, endpoint, **kwargs)
        return body

    def _make_request_with_headers(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> tuple[dict, dict]:
        """
        Idem a _make_request mas devolve (body, headers) para acesso ao Link header.
        Raises:
            requests.HTTPError: erro HTTP não recuperável após retries
            requests.RequestException: falha de rede após retries
            RuntimeError: todos os retries esgotados em rate limit
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json(), dict(response.headers)
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

        raise RuntimeError(f"Rate limit Shopify persistente após {self.MAX_RETRIES} tentativas: {url}")
