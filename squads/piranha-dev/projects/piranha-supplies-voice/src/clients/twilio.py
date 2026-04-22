"""Cliente Twilio — dispara ligações via API Key usando processamento regional Twilio."""

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TwilioClient:
    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self) -> None:
        """
        Inicializa o cliente com autenticação via API Key regional.
        Para regiões não-US, o hostname deve incluir edge + region
        (ex: api.dublin.ie1.twilio.com) para garantir processamento nessa região.
        """
        self.base_url = self._build_base_url()
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth = (Config.TWILIO_API_KEY_SID, Config.TWILIO_API_KEY_SECRET)
        self.session = requests.Session()

    @staticmethod
    def _build_base_url() -> str:
        """
        Constrói o base URL correto do Twilio REST API para a região configurada.

        US1 usa api.twilio.com.
        Regiões como IE1/AU1 exigem o formato api.<edge>.<region>.twilio.com.
        """
        region = (Config.TWILIO_REGION or "").strip().lower()
        edge = (Config.TWILIO_EDGE or "").strip().lower()

        if not region or region == "us1":
            return TwilioClient.BASE_URL

        if not edge:
            raise ValueError("TWILIO_EDGE é obrigatório quando TWILIO_REGION não é us1")

        return f"https://api.{edge}.{region}.twilio.com/2010-04-01"

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
            ("StatusCallbackEvent", "no-answer"),
            ("StatusCallbackEvent", "busy"),
            ("StatusCallbackEvent", "failed"),
            ("StatusCallbackEvent", "canceled"),
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
            f"| edge={Config.TWILIO_EDGE} | region={Config.TWILIO_REGION} | base_url={self.base_url}"
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
