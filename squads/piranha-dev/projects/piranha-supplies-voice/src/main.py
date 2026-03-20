"""Entry point do cron — executa o fluxo diário de ligações outbound."""

from src.clients.shopify import ShopifyClient
from src.config import Config
from src.handlers.call_handler import process_checkouts
from src.utils.logger import setup_logger
from src.utils.schedule_checker import is_calling_hours

logger = setup_logger(__name__)


def main() -> None:
    """
    Fluxo principal:
    1. Valida configuração
    2. Verifica janela de chamadas (11:00–12:00 e 14:30–17:00, Europe/Lisbon)
    3. Busca checkouts abandonados há 7+ dias (apenas EU)
    4. Processa ligações de forma sequencial
    """
    logger.info("=== Piranha Supplies Voice — Início ===")

    # 1. Validar configuração
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuração inválida: {e}")
        return

    # 2. Verificar janela de chamadas
    if not is_calling_hours():
        logger.info("Fora da janela de chamadas (11:00–12:00 ou 14:30–17:00). A encerrar.")
        return

    # 3. Buscar checkouts abandonados há 7–14 dias (call_tracker evita re-contacto)
    try:
        shopify = ShopifyClient()
        checkouts = shopify.get_abandoned_checkouts(day_min=14, day_max=7)
    except Exception as e:
        logger.error(f"Erro ao contactar Shopify: {e}")
        return

    if not checkouts:
        logger.info("Nenhum checkout elegível na janela de 7–14 dias. A encerrar.")
        return

    # 4. Processar ligações de forma sequencial
    process_checkouts(checkouts)

    logger.info("=== Piranha Supplies Voice — Concluído ===")


if __name__ == "__main__":
    main()
