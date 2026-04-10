"""Normaliza números de telefone para formato E.164 antes de passar ao Twilio."""

# Código de marcação por país ISO 3166-1 (União Europeia + países relevantes)
_DIALING_CODES: dict[str, str] = {
    "AT": "43",
    "BE": "32",
    "BG": "359",
    "CY": "357",
    "CZ": "420",
    "DE": "49",
    "DK": "45",
    "EE": "372",
    "ES": "34",
    "FI": "358",
    "FR": "33",
    "GR": "30",
    "HR": "385",
    "HU": "36",
    "IE": "353",
    "IT": "39",
    "LT": "370",
    "LU": "352",
    "LV": "371",
    "MT": "356",
    "NL": "31",
    "PL": "48",
    "PT": "351",
    "RO": "40",
    "SE": "46",
    "SI": "386",
    "SK": "421",
    # Extra
    "GB": "44",
    "BR": "55",
    "US": "1",
    "CH": "41",
}

_MIN_DIGITS = 8  # mínimo de dígitos para um número válido (código de país + local)


def normalize_phone(raw: str, country_code: str = "") -> str | None:
    """
    Normaliza um número de telefone para formato E.164 (+<código><número>).

    Passos:
      1. Remove todos os caracteres não-dígitos (exceto '+' inicial)
      2. Remove prefixo "00" de chamada internacional
      3. Se não começar por '+' e tivermos o country_code, adiciona o código de marcação
      4. Garante que começa com '+'
      5. Valida comprimento mínimo

    Args:
        raw: número bruto (ex: "910123456", "+351910123456", "00351910123456")
        country_code: ISO 3166-1 alpha-2 (ex: "PT", "ES") — usado para adicionar prefixo

    Returns:
        Número em E.164 (ex: "+351910123456") ou None se inválido
    """
    if not raw:
        return None

    # Preservar '+' inicial se existir
    has_plus = raw.strip().startswith("+")

    # Remover tudo exceto dígitos
    digits = "".join(c for c in raw if c.isdigit())

    if not digits:
        return None

    # Remover prefixo "00" de marcação internacional
    if digits.startswith("00"):
        digits = digits[2:]
        has_plus = False  # já removemos o prefixo, tratar como número sem '+'

    dialing = _DIALING_CODES.get(country_code.upper(), "") if country_code else ""

    if not has_plus and dialing:
        # Número local — remover zeros à esquerda e adicionar código do país
        local = digits.lstrip("0") or digits
        if not local.startswith(dialing):
            digits = dialing + local
        else:
            digits = local

    # Validar comprimento mínimo
    if len(digits) < _MIN_DIGITS:
        return None

    return "+" + digits


def is_valid_phone(raw: str, country_code: str = "") -> bool:
    """Retorna True se o número puder ser normalizado para E.164."""
    return normalize_phone(raw, country_code) is not None
