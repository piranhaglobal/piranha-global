"""Cliente Evolution API — envio de mensagens WhatsApp."""

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class EvolutionClient:

    def __init__(self) -> None:
        """Inicializa sessão HTTP com apikey."""
        self.base_url = Config.EVOLUTION_API_URL.rstrip("/")
        self.instance = Config.EVOLUTION_INSTANCE
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": Config.EVOLUTION_API_KEY,
            "Content-Type": "application/json",
        })

    def send_text(self, to_number: str, text: str) -> dict:
        """
        Envia mensagem de texto WhatsApp.
        Args:
            to_number: número normalizado sem + (ex: "351912345678")
            text: corpo da mensagem (suporta \n)
        Returns:
            dict com key.id da mensagem enviada
        Raises:
            requests.HTTPError: instância offline ou número inválido
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": to_number,
            "text": text,
            "delay": 1200,  # simula digitação humana
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        msg_id = data.get("key", {}).get("id", "")
        logger.info(f"WhatsApp enviado | to={to_number} | msg_id={msg_id}")
        return data

    def check_instance(self) -> bool:
        """
        Verifica se a instância WhatsApp está conectada.
        Returns:
            True se status == "open"
        """
        try:
            url = f"{self.base_url}/instance/connectionState/{self.instance}"
            response = self.session.get(url)
            response.raise_for_status()
            state = response.json().get("instance", {}).get("state", "")
            connected = state == "open"
            if not connected:
                logger.warning(f"Instância WhatsApp offline: state={state}")
            return connected
        except Exception as e:
            logger.error(f"Erro ao verificar instância Evolution: {e}")
            return False
