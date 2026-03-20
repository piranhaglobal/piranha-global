"""Normaliza números de telefone para o formato aceite pela Evolution API."""

import re

from src.utils.language_detector import get_phone_prefix
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def normalize(phone: str, country_code: str = "PT") -> str | None:
    """
    Normaliza número de telefone para formato Evolution API (só dígitos, com DDI).

    Casos tratados:
        "+351 912 345 678" → "351912345678"
        "00351912345678"   → "351912345678"
        "912345678" + "PT" → "351912345678"
        "+34 612 345 678"  → "34612345678"
        ""  ou None        → None

    Args:
        phone: número em qualquer formato
        country_code: ISO 3166-1 alpha-2 para inferir DDI se ausente
    Returns:
        string normalizada com apenas dígitos e DDI, ou None se inválido
    """
    if not phone or not phone.strip():
        return None

    digits = _strip_formatting(phone)

    if not digits:
        return None

    # Remove prefixo 00 (ex: 00351...) — equivalente ao +
    if digits.startswith("00"):
        digits = digits[2:]

    # Se não tem DDI, adiciona com base no país do endereço
    if not _has_country_code(digits):
        prefix = get_phone_prefix(country_code)
        if not prefix:
            logger.warning(
                f"Prefixo não encontrado para país '{country_code}'. "
                f"A usar número sem DDI: {digits}"
            )
        else:
            digits = prefix + digits

    # Validação mínima: pelo menos 8 dígitos
    if len(digits) < 8:
        logger.warning(f"Número inválido após normalização: {digits}")
        return None

    return digits


def _strip_formatting(phone: str) -> str:
    """
    Remove todos os caracteres não numéricos (espaços, hífens, parênteses, +).
    Args:
        phone: número com qualquer formatação
    Returns:
        string apenas com dígitos
    """
    return re.sub(r"[^\d]", "", phone)


def _has_country_code(digits: str) -> bool:
    """
    Heurística: números com mais de 10 dígitos provavelmente já têm DDI.
    Um número local máximo tem 10 dígitos (ex: Brasil: 11 999999999).
    Args:
        digits: número apenas com dígitos
    Returns:
        True se provavelmente já tem DDI
    """
    return len(digits) > 10
