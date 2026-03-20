"""Entry point do cron — executa o fluxo diário de disparos WhatsApp pós-compra."""

from src.clients.evolution import EvolutionClient
from src.clients.shopify import ShopifyClient
from src.config import Config
from src.handlers.message_handler import process_orders
from src.utils.logger import setup_logger
from src.utils.schedule_checker import is_business_hours

logger = setup_logger(__name__)


def main() -> None:
    """
    Fluxo principal:
    1. Valida configuração
    2. Verifica horário comercial (Europe/Lisbon)
    3. Verifica instância WhatsApp online
    4. Actualiza cache de produtos consumíveis
    5. Busca pedidos do dia 25
    6. Processa disparos com delay de 300s entre leads
    """
    logger.info("=== Piranha Supplies — Post Purchase WhatsApp — Início ===")

    # 1. Validar configuração
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuração inválida: {e}")
        return

    # 2. Verificar horário comercial (seg–sáb 08h–20h)
    if not is_business_hours("Europe/Lisbon"):
        logger.info("Fora do horário comercial (seg–sáb 08h–20h). A encerrar.")
        return

    # 3. Verificar instância WhatsApp
    evolution = EvolutionClient()
    if not evolution.check_instance():
        logger.error("Instância WhatsApp offline. A encerrar.")
        return

    shopify = ShopifyClient()

    # 4. Actualizar cache de consumíveis
    try:
        consumable_ids = shopify.get_consumable_ids()
    except Exception as e:
        logger.error(f"Erro ao obter produtos consumíveis: {e}")
        return

    if not consumable_ids:
        logger.warning(
            "Colecção de consumíveis vazia ou não encontrada. "
            "Todos os pedidos serão tratados como Segmento C."
        )

    # 5. Buscar pedidos do dia 25
    try:
        orders = shopify.get_orders_day_25()
    except Exception as e:
        logger.error(f"Erro ao contactar Shopify: {e}")
        return

    if not orders:
        logger.info("Nenhum pedido no dia 25. A encerrar.")
        return

    # 6. Processar disparos
    process_orders(orders, consumable_ids)

    logger.info("=== Piranha Supplies — Post Purchase WhatsApp — Concluído ===")


if __name__ == "__main__":
    main()
