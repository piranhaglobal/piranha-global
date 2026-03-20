"""Segmentação, geração de mensagem e coordenação de envios com delay obrigatório."""

import time

from src.clients.evolution import EvolutionClient
from src.prompts.messages import build_message
from src.utils import sent_tracker
from src.utils.language_detector import get_language
from src.utils.logger import setup_logger
from src.utils.phone_normalizer import normalize

logger = setup_logger(__name__)

# ─── Delay obrigatório entre leads — NÃO ALTERAR ─────────────────────────────
# Conta WhatsApp foi desactivada com delays menores.
# Mínimo seguro confirmado pela equipa: 300 segundos entre cada envio.
_SEND_DELAY_SECONDS = 300
# ─────────────────────────────────────────────────────────────────────────────


def process_orders(
    orders: list[dict],
    consumable_ids: set[int],
) -> None:
    """
    Processa lista de pedidos com delay de 300s entre cada envio.
    Args:
        orders: lista normalizada de pedidos do ShopifyClient
        consumable_ids: set de product_ids consumíveis
    """
    if not orders:
        logger.info("Nenhum pedido elegível para disparar hoje.")
        return

    total = len(orders)
    logger.info(f"A iniciar processamento de {total} pedido(s)")

    for idx, order in enumerate(orders, start=1):
        logger.info(f"[{idx}/{total}] A processar pedido {order['id']}")
        status = process_single(order, consumable_ids)
        logger.info(f"[{idx}/{total}] Pedido {order['id']} → {status}")

        # Delay obrigatório entre leads — só aplica após envio real
        if status == "sent" and idx < total:
            logger.info(
                f"A aguardar {_SEND_DELAY_SECONDS}s antes do próximo envio "
                f"(anti-ban obrigatório)..."
            )
            time.sleep(_SEND_DELAY_SECONDS)


def process_single(
    order: dict,
    consumable_ids: set[int],
) -> str:
    """
    Processa um único pedido: verifica duplicata → normaliza telefone →
    classifica → gera mensagem → envia.
    Args:
        order: dict com id, phone, name, country_code, line_items
        consumable_ids: set de product_ids consumíveis
    Returns:
        "sent" | "already_sent_skip" | "no_phone_skip" | "error"
    """
    order_id = order["id"]
    country_code = order.get("country_code", "PT")

    # 1. Verificar duplicata
    if sent_tracker.is_sent(order_id):
        sent_tracker.mark(order_id, order["phone"], order["name"], "-", "-", "already_sent_skip")
        logger.info(f"Skip: pedido {order_id} já foi disparado anteriormente.")
        return "already_sent_skip"

    # 2. Normalizar telefone
    phone = normalize(order.get("phone", ""), country_code)
    if not phone:
        sent_tracker.mark(order_id, "", order["name"], "-", "-", "no_phone_skip")
        logger.warning(f"Skip: pedido {order_id} sem telefone válido.")
        return "no_phone_skip"

    # 3. Detectar idioma
    language = get_language(country_code)

    # 4. Classificar pedido por segmento
    segment, consumable_titles = classify(order.get("line_items", []), consumable_ids)

    # 5. Gerar mensagem
    try:
        message = build_message(segment, language, order["name"], consumable_titles)
    except ValueError as e:
        logger.error(f"Erro ao gerar mensagem para pedido {order_id}: {e}")
        sent_tracker.mark(order_id, phone, order["name"], segment, language, "error")
        return "error"

    # 6. Enviar
    try:
        client = EvolutionClient()
        client.send_text(phone, message)
        sent_tracker.mark(order_id, phone, order["name"], segment, language, "sent")
        return "sent"
    except Exception as e:
        logger.error(f"Erro ao enviar WhatsApp para pedido {order_id}: {e}")
        sent_tracker.mark(order_id, phone, order["name"], segment, language, "error")
        return "error"


def classify(
    line_items: list[dict],
    consumable_ids: set[int],
) -> tuple[str, list[str]]:
    """
    Classifica o pedido e extrai os títulos dos consumíveis comprados.
    Args:
        line_items: lista de {product_id, title}
        consumable_ids: set de product_ids consumíveis
    Returns:
        tuple: (segmento, lista_titulos_consumiveis)
        "A_B" se o pedido contém pelo menos um consumível
        "C"   se o pedido não contém nenhum consumível
    """
    consumable_titles = [
        item["title"]
        for item in line_items
        if item.get("product_id") in consumable_ids
    ]

    segment = "A_B" if consumable_titles else "C"
    return segment, consumable_titles
