"""Verifica se o momento atual está dentro das janelas de chamadas permitidas."""

from datetime import date, datetime, timedelta

import pytz

# Timezone de referência (Portugal)
_TZ_DEFAULT = "Europe/Lisbon"

# Janelas de chamada em minutos desde meia-noite (hora local do país de destino)
# 11:00–12:30  →  660–750
# 14:00–17:00  →  840–1020
_CALL_WINDOWS = [
    (11 * 60,       12 * 60 + 30),  # 11:00 – 12:30
    (14 * 60,       17 * 60),        # 14:00 – 17:00
]

# Timezone IANA por código de país (União Europeia)
# Cada lead é verificado no horário LOCAL do seu país — nunca no horário de Portugal.
_COUNTRY_TIMEZONE: dict[str, str] = {
    "AT": "Europe/Vienna",
    "BE": "Europe/Brussels",
    "BG": "Europe/Sofia",
    "CY": "Asia/Nicosia",
    "CZ": "Europe/Prague",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "EE": "Europe/Tallinn",
    "ES": "Europe/Madrid",
    "FI": "Europe/Helsinki",
    "FR": "Europe/Paris",
    "GR": "Europe/Athens",
    "HR": "Europe/Zagreb",
    "HU": "Europe/Budapest",
    "IE": "Europe/Dublin",
    "IT": "Europe/Rome",
    "LT": "Europe/Vilnius",
    "LU": "Europe/Luxembourg",
    "LV": "Europe/Riga",
    "MT": "Europe/Malta",
    "NL": "Europe/Amsterdam",
    "PL": "Europe/Warsaw",
    "PT": "Europe/Lisbon",
    "RO": "Europe/Bucharest",
    "SE": "Europe/Stockholm",
    "SI": "Europe/Ljubljana",
    "SK": "Europe/Bratislava",
}


def get_country_timezone(country_code: str) -> str:
    """Retorna o timezone IANA para o código de país dado."""
    return _COUNTRY_TIMEZONE.get(country_code.upper(), _TZ_DEFAULT)


def is_calling_hours(country_code: str | None = None) -> bool:
    """
    Verifica se agora é janela de chamadas no timezone de Lisboa (Europe/Lisbon).
    Janelas: seg–sex, 11:00–12:30 e 14:00–17:00 (hora de Lisboa).

    O parâmetro country_code é aceite mas ignorado — todas as chamadas
    seguem o horário de Portugal independentemente do país do cliente.

    Args:
        country_code: ignorado (mantido para compatibilidade de interface)
    Returns:
        True se dentro de uma janela de chamada
    """
    tz = pytz.timezone(_TZ_DEFAULT)
    now = datetime.now(tz)

    # Só dias úteis (seg=0 … sex=4)
    if now.weekday() > 4:
        return False

    minutes = now.hour * 60 + now.minute
    return any(start <= minutes < end for start, end in _CALL_WINDOWS)


def next_business_day(from_date: date | None = None) -> date:
    """
    Retorna o próximo dia útil (seg–sex) a partir de from_date (exclusive).
    Se from_date é sexta, retorna segunda-feira seguinte.
    Se from_date é sábado ou domingo, retorna segunda-feira.
    Se from_date é None, usa hoje.

    Exemplos:
      - sexta 2026-03-20 → segunda 2026-03-23
      - sábado 2026-03-21 → segunda 2026-03-23
      - segunda 2026-03-23 → terça 2026-03-24
    """
    d = from_date or date.today()
    d += timedelta(days=1)
    while d.weekday() > 4:  # 5=sábado, 6=domingo
        d += timedelta(days=1)
    return d


# Alias para compatibilidade com código existente
is_business_hours = is_calling_hours
