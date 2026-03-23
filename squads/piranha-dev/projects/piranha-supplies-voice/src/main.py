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
    2. Verifica janela de chamadas no timezone de Portugal (11:00–12:30 e 14:00–17:00, seg–sex)
    3. Busca novos checkouts abandonados no Shopify
    4. Processa retries pendentes + novos leads de forma sequencial
       — Cada lead é verificado no timezone do SEU país antes de ligar
       — Leads sem resposta são agendados para o próximo dia útil (máx. 2 tentativas)
       — Países fora da União Europeia são ignorados
    """
    logger.info("=== Piranha Supplies Voice — Início ===")

    # 1. Validar configuração
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuração inválida: {e}")
        return

    # 2. Verificar janela de chamadas (timezone Portugal como guarda de entrada)
    if not is_calling_hours():
        logger.info("Fora da janela de chamadas (11:00–12:30 ou 14:00–17:00). A encerrar.")
        return

    # 3. Buscar checkouts abandonados há 7–14 dias (call_tracker evita re-contacto)
    try:
        shopify = ShopifyClient()
        checkouts = shopify.get_abandoned_checkouts(day_min=14, day_max=7)
    except Exception as e:
        logger.error(f"Erro ao contactar Shopify: {e}")
        return

    # 4. Processar retries pendentes e novos leads
    process_checkouts(checkouts)

    logger.info("=== Piranha Supplies Voice — Concluído ===")


if __name__ == "__main__":
    main()
