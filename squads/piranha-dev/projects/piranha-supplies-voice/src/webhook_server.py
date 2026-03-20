"""Entry point do servidor de webhook — processo contínuo na VPS."""

from src.config import Config
from src.handlers.webhook_handler import create_app
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

if __name__ == "__main__":
    app = create_app()
    logger.info(f"Webhook server a iniciar na porta {Config.WEBHOOK_PORT}")
    app.run(host="0.0.0.0", port=Config.WEBHOOK_PORT)
