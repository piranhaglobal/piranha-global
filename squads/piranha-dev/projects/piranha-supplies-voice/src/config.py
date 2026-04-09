"""Carrega e valida as variáveis de ambiente do projeto."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Shopify
    SHOPIFY_STORE_URL: str = os.getenv("SHOPIFY_STORE_URL", "")          # myshopify.com (API)
    SHOPIFY_STOREFRONT_URL: str = os.getenv("SHOPIFY_STOREFRONT_URL", "") # domínio público (FAQs/scraping)
    SHOPIFY_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    SHOPIFY_API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2024-10")

    # Ultravox
    ULTRAVOX_API_KEY: str = os.getenv("ULTRAVOX_API_KEY", "")

    # Ultravox — voz nativa clonada (substitui Cartesia)
    ULTRAVOX_VOICE_ID: str = os.getenv("ULTRAVOX_VOICE_ID", "")

    # Cartesia (voz externa via Ultravox externalVoice — mantido como fallback)
    CARTESIA_API_KEY: str = os.getenv("CARTESIA_API_KEY", "")
    CARTESIA_VOICE_ID: str = os.getenv("VOICE_ID", "")  # variável no .env é VOICE_ID

    # Twilio — credenciais principais
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")

    # Twilio — API Key (autenticação preferencial para região IE1)
    TWILIO_API_KEY_SID: str = os.getenv("TWILIO_API_KEY_SID", "")
    TWILIO_API_KEY_SECRET: str = os.getenv("TWILIO_API_KEY_SECRET", "")

    # Twilio — roteamento regional
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")  # E.164: +351...
    TWILIO_EDGE: str = os.getenv("TWILIO_EDGE", "dublin")
    TWILIO_REGION: str = os.getenv("TWILIO_REGION", "ie1")

    # VPS
    VPS_BASE_URL: str = os.getenv("VPS_BASE_URL", "")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "5000"))

    _REQUIRED = [
        "SHOPIFY_STORE_URL",
        "SHOPIFY_ACCESS_TOKEN",
        "ULTRAVOX_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_API_KEY_SID",
        "TWILIO_API_KEY_SECRET",
        "TWILIO_FROM_NUMBER",
        "VPS_BASE_URL",
    ]

    @classmethod
    def validate(cls) -> None:
        """
        Valida que todas as variáveis obrigatórias estão presentes.
        Raises:
            ValueError: com lista das variáveis ausentes.
        """
        missing = [k for k in cls._REQUIRED if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Variáveis de ambiente ausentes: {missing}")
