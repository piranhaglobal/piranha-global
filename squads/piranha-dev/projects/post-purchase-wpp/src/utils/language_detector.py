"""Mapeia código de país para idioma e prefixo telefónico."""

# País → idioma
COUNTRY_LANGUAGE_MAP: dict[str, str] = {
    # Português
    "PT": "pt", "BR": "pt", "AO": "pt", "MZ": "pt", "CV": "pt",
    "GW": "pt", "ST": "pt", "TL": "pt",
    # Espanhol
    "ES": "es", "MX": "es", "AR": "es", "CO": "es", "CL": "es",
    "PE": "es", "VE": "es", "EC": "es", "UY": "es", "PY": "es",
    "BO": "es", "CR": "es", "PA": "es", "DO": "es", "GT": "es",
    "HN": "es", "SV": "es", "NI": "es", "CU": "es",
    # Francês
    "FR": "fr", "BE": "fr", "LU": "fr", "MC": "fr",
    "SN": "fr", "CI": "fr", "CM": "fr", "ML": "fr", "BF": "fr",
    "NE": "fr", "TD": "fr", "CG": "fr", "GA": "fr", "MG": "fr",
    # Inglês — fallback explícito para países comuns
    "GB": "en", "US": "en", "IE": "en", "AU": "en", "NZ": "en",
    "CA": "en", "ZA": "en", "NG": "en", "GH": "en", "KE": "en",
    "DE": "en", "IT": "en", "NL": "en", "PL": "en", "SE": "en",
    "NO": "en", "DK": "en", "FI": "en", "AT": "en", "CH": "en",
}

# País → prefixo telefónico (DDI) sem o +
COUNTRY_PHONE_PREFIX: dict[str, str] = {
    "PT": "351", "ES": "34",  "FR": "33",  "GB": "44",
    "DE": "49",  "IT": "39",  "NL": "31",  "BE": "32",
    "AT": "43",  "CH": "41",  "SE": "46",  "NO": "47",
    "DK": "45",  "FI": "358", "PL": "48",  "IE": "353",
    "BR": "55",  "MX": "52",  "AR": "54",  "CO": "57",
    "CL": "56",  "PE": "51",  "VE": "58",  "EC": "593",
    "US": "1",   "CA": "1",   "AU": "61",  "NZ": "64",
    "AO": "244", "MZ": "258", "CV": "238", "ZA": "27",
    "NG": "234", "GH": "233", "KE": "254", "SN": "221",
}


def get_language(country_code: str) -> str:
    """
    Retorna o código de idioma para um país.
    Args:
        country_code: ISO 3166-1 alpha-2 (ex: "PT", "DE", "FR")
    Returns:
        "pt", "es", "fr" ou "en" (fallback para países não mapeados)
    """
    return COUNTRY_LANGUAGE_MAP.get((country_code or "").upper(), "en")


def get_phone_prefix(country_code: str) -> str:
    """
    Retorna o prefixo telefónico (DDI) para um país.
    Args:
        country_code: ISO 3166-1 alpha-2
    Returns:
        string do DDI sem + (ex: "351", "34")
        "" se país não mapeado
    """
    return COUNTRY_PHONE_PREFIX.get((country_code or "").upper(), "")
