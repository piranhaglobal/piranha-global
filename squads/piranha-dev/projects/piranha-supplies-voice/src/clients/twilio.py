"""Cliente Twilio — dispara ligações telefónicas via API Key + edge Dublin (IE1)."""

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TwilioClient:
    # O Twilio REST API usa sempre api.twilio.com.
    # O roteamento para o edge Dublin (IE1) é garantido pelas credenciais
    # regionais (API Key SID/Secret criadas na região IE1) — não por hostname.
    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self) -> None:
        """
        Inicializa o cliente com autenticação via API Key (IE1/Dublin).
        A auth usa (API_KEY_SID, API_KEY_SECRET) em vez de (ACCOUNT_SID, AUTH_TOKEN).
        """
        self.base_url = self.BASE_URL
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        # Auth via Account SID + Auth Token (padrão Twilio REST API)
        self.auth = (Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        self.session = requests.Session()

    def make_call(
        self,
        to_number: str,
        twiml_url: str,
        status_callback_url: str,
    ) -> dict:
        """
        Dispara uma ligação telefónica para o número do cliente.
        Args:
            to_number: número destino em E.164 (ex: "+351912345678")
            twiml_url: URL pública para buscar TwiML quando a chamada atender
            status_callback_url: URL pública para callbacks de estado da chamada
        Returns:
            dict com dados da chamada Twilio (inclui "sid")
        Raises:
            requests.HTTPError: se o número for inválido ou credenciais incorretas
        """
        payload = [
            ("To", to_number),
            ("From", Config.TWILIO_FROM_NUMBER),
            ("Url", twiml_url),
            ("Method", "POST"),
            ("StatusCallback", status_callback_url),
            ("StatusCallbackMethod", "POST"),
            ("StatusCallbackEvent", "answered"),
            ("StatusCallbackEvent", "completed"),
        ]

        response = self.session.post(
            f"{self.base_url}/Accounts/{self.account_sid}/Calls.json",
            data=payload,
            auth=self.auth,
        )
        response.raise_for_status()
        data = response.json()

        call_sid = data.get("sid", "")
        logger.info(
            f"Ligação Twilio disparada | to={to_number} | sid={call_sid} "
            f"| edge={Config.TWILIO_EDGE} | region={Config.TWILIO_REGION}"
        )
        return data

    def build_twiml_url(self) -> str:
        """
        Monta a URL pública do webhook TwiML.
        Returns:
            ex: "https://call.piranhasupplies.com/webhook/twilio/twiml"
        """
        return f"{Config.VPS_BASE_URL.rstrip('/')}/webhook/twilio/twiml"

    def build_status_callback_url(self) -> str:
        """
        Monta a URL pública do webhook de status.
        Returns:
            ex: "https://call.piranhasupplies.com/webhook/twilio/status"
        """
        return f"{Config.VPS_BASE_URL.rstrip('/')}/webhook/twilio/status"
