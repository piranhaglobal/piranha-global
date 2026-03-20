"""Definicoes de tipos partilhados (TypedDict, Literal) usados em todo o projecto."""

from typing import Literal, TypedDict


# --- Tipo de disparo ---

DispatchType = Literal["D1", "D2", "D3", "D4"]


# --- Prioridades por disparo ---

DISPATCH_PRIORITY: dict[DispatchType, int] = {
    "D1": 1,  # Confirmacao -- maior urgencia
    "D2": 2,  # Tracking
    "D3": 3,  # Delay notification
    "D4": 4,  # Reorder -- menor urgencia
}


# --- Dados normalizados de um pedido ---

class LineItem(TypedDict):
    """Item de linha de um pedido Shopify."""
    product_id: int | None
    title: str
    quantity: int
    price: str


class OrderData(TypedDict, total=False):
    """Dados normalizados de um pedido, usados em todos os dispatches.

    Campos obrigatorios:
        id: ID do pedido Shopify (string)
        phone: telefone em formato E.164 (pode ser vazio)
        name: primeiro nome do cliente
        country_code: ISO 3166-1 alpha-2

    Campos opcionais (depende do dispatch):
        order_name: numero legivel (#XXXX)
        customer_id: ID do customer Shopify
        line_items: lista de itens do pedido
        total_price: valor total como string decimal
        currency: ISO 4217 (ex: EUR)
        fulfillment_status: null | "partial" | "fulfilled"
        created_at: data ISO 8601 de criacao do pedido
    """
    # Obrigatorios
    id: str
    phone: str
    name: str
    country_code: str
    # Opcionais
    order_name: str
    customer_id: str
    line_items: list[LineItem]
    total_price: str
    currency: str
    fulfillment_status: str | None
    created_at: str


# --- Item da fila de mensagens ---

class QueueItemData(TypedDict, total=False):
    """Dados especificos por tipo de dispatch dentro do queue item.

    D1: line_items, total_price, currency
    D2: tracking_url, tracking_number, tracking_company
    D3: order_name (para template)
    D4: segment, consumable_titles, line_items
    """
    line_items: list[LineItem]
    total_price: str
    currency: str
    tracking_url: str
    tracking_number: str
    tracking_company: str
    segment: str
    consumable_titles: list[str]
    order_name: str


class QueueItem(TypedDict):
    """Item na fila de mensagens (queue.json).

    Formato canonico usado por queue_handler, webhook_handler,
    cron_d3, cron_d4 e message_worker.

    Atributos:
        id: UUID v4 gerado no enqueue
        dispatch_type: "D1" | "D2" | "D3" | "D4"
        priority: 1 (D1) a 4 (D4) -- menor = mais urgente
        order_id: ID do pedido Shopify (string)
        order_name: numero legivel (#XXXX)
        customer_name: primeiro nome do cliente
        customer_id: ID do customer Shopify (string)
        phone: telefone em formato bruto (sera normalizado pelo worker)
        country_code: ISO 3166-1 alpha-2
        needs_order_fetch: True se dados do cliente precisam ser buscados na Shopify
        enqueued_at: ISO 8601 UTC timestamp de enfileiramento
        data: dados especificos do dispatch
    """
    id: str
    dispatch_type: DispatchType
    priority: int
    order_id: str
    order_name: str
    customer_name: str
    customer_id: str
    phone: str
    country_code: str
    needs_order_fetch: bool
    enqueued_at: str
    data: QueueItemData


# --- Registo no sent_tracker ---

class DispatchRecord(TypedDict, total=False):
    """Registo de um dispatch individual dentro do sent_tracker.

    Atributos:
        status: estado do dispatch
        timestamp: ISO 8601 do momento do registo
        msg_id: ID da mensagem Evolution API (se enviada)
        segment: segmento D4 (A/B/C) -- apenas para D4
        tracking_url: URL de tracking -- apenas para D2
    """
    status: str
    timestamp: str
    msg_id: str
    segment: str
    tracking_url: str


class SentRecord(TypedDict):
    """Registo de um pedido no sent_tracker v2 (sent.json).

    Atributos:
        phone: telefone normalizado
        name: primeiro nome do cliente
        country_code: ISO 3166-1 alpha-2
        language: codigo de idioma (pt/es/fr/en)
        dispatches: mapa dispatch_type -> DispatchRecord
    """
    phone: str
    name: str
    country_code: str
    language: str
    dispatches: dict[str, DispatchRecord]
