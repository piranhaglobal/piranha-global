"""Verifica se o momento atual está dentro das janelas de chamadas permitidas."""

from datetime import datetime

import pytz

# Timezone de referência
_TZ = "Europe/Lisbon"

# Janelas de chamada em minutos desde meia-noite
# 11:00–12:00  →  660–720
# 14:30–17:00  →  870–1020
_CALL_WINDOWS = [
    (11 * 60, 12 * 60),       # 11:00 – 12:00
    (14 * 60 + 30, 17 * 60),  # 14:30 – 17:00
]


def is_calling_hours(timezone: str = _TZ) -> bool:
    """
    Verifica se agora é uma janela de chamadas permitida (Portugal).
    Janelas: seg–sex, 11:00–12:00 e 14:30–17:00 (Europe/Lisbon).
    Args:
        timezone: timezone IANA (default: Europe/Lisbon)
    Returns:
        True se dentro de uma janela de chamada
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # Só dias úteis (seg=0 … sex=4)
    if now.weekday() > 4:
        return False

    minutes = now.hour * 60 + now.minute
    return any(start <= minutes < end for start, end in _CALL_WINDOWS)


# Alias para compatibilidade com main.py existente
is_business_hours = is_calling_hours
