"""Mapeia código de país ISO 3166-1 para idioma da ligação."""

# Regra da empresa (apenas UE):
#   Portugal  → português
#   Espanha   → espanhol
#   França    → francês
#   Todos os outros países da UE → inglês
COUNTRY_LANGUAGE_MAP: dict[str, str] = {
    "PT": "pt",
    "ES": "es",
    "FR": "fr",
}

# Voz Ultravox por idioma
# PedroPiranha = voz personalizada da conta Ultravox da Piranha
_VOICE_MAP: dict[str, str] = {
    "pt": "PedroPiranha",
    "es": "Miguel",
    "fr": "Mathieu",
    "en": "Matt",
}

# languageHint aceite pela Ultravox API
_ULTRAVOX_HINT_MAP: dict[str, str] = {
    "pt": "pt",
    "es": "es",
    "fr": "fr",
    "en": "en",
}


def get_language(country_code: str) -> str:
    """
    Retorna o código de idioma para um país.
    Args:
        country_code: código ISO 3166-1 alpha-2 (ex: "PT", "DE", "FR")
    Returns:
        "pt", "es", "fr" ou "en" (fallback para países não mapeados)
    """
    return COUNTRY_LANGUAGE_MAP.get((country_code or "").upper(), "en")


def get_ultravox_hint(language: str) -> str:
    """
    Retorna o languageHint compatível com a Ultravox API.
    Args:
        language: "pt", "es", "fr" ou "en"
    Returns:
        string do languageHint
    """
    return _ULTRAVOX_HINT_MAP.get(language, "en")


def get_voice_for_language(language: str) -> str:
    """
    Retorna a voz Ultravox mais adequada para o idioma.
    Args:
        language: "pt", "es", "fr" ou "en"
    Returns:
        nome da voz Ultravox
    """
    return _VOICE_MAP.get(language, "Emily")
