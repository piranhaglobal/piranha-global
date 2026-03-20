"""Carrega e valida as variáveis de ambiente do projecto."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Shopify ---
    SHOPIFY_STORE_URL: str = os.getenv("SHOPIFY_STORE_URL", "")
    SHOPIFY_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    SHOPIFY_API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    SHOPIFY_CONSUMABLES_HANDLE: str = os.getenv(
        "SHOPIFY_CONSUMABLES_HANDLE", "consumables-and-hygiene"
    )
    SHOPIFY_WEBHOOK_SECRET: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

    # --- Evolution API ---
    EVOLUTION_API_URL: str = os.getenv("EVOLUTION_API_URL", "")
    EVOLUTION_API_KEY: str = os.getenv("EVOLUTION_API_KEY", "")
    EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "")

    # --- Servidor Webhook ---
    WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    # --- Delay obrigatório entre leads — NÃO ALTERAR ---
    # Conta WhatsApp foi desactivada com delays menores
    SEND_DELAY_SECONDS: int = int(os.getenv("SEND_DELAY_SECONDS", "300"))

    # --- Conteúdo Opcional ---
    EDUCATIONAL_CONTENT_URL: str = os.getenv("EDUCATIONAL_CONTENT_URL", "")
    REVIEW_REQUEST_FILE: str = os.getenv("REVIEW_REQUEST_FILE", "")

    # --- Listas de variáveis obrigatórias por modo ---
    _REQUIRED_BASE: list[str] = [
        "SHOPIFY_STORE_URL",
        "SHOPIFY_ACCESS_TOKEN",
        "EVOLUTION_API_URL",
        "EVOLUTION_API_KEY",
        "EVOLUTION_INSTANCE",
    ]

    _REQUIRED_WEBHOOK: list[str] = _REQUIRED_BASE + [
        "SHOPIFY_WEBHOOK_SECRET",
    ]

    @classmethod
    def validate(cls, mode: str = "base") -> None:
        """
        Valida que todas as variáveis obrigatórias estão presentes.

        Dois modos:
          - "base": valida variáveis mínimas (para cron D3/D4 e worker)
          - "webhook": valida variáveis base + SHOPIFY_WEBHOOK_SECRET (para webhook server)

        Args:
            mode: "base" (default) ou "webhook"

        Raises:
            ValueError: com lista das variáveis ausentes
        """
        if mode == "webhook":
            required = cls._REQUIRED_WEBHOOK
        else:
            required = cls._REQUIRED_BASE

        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Variáveis de ambiente ausentes: {missing}")
