"""Verifica horário comercial para envios WhatsApp."""

from datetime import datetime
import pytz

# seg=0 a sáb=5 — domingo excluído
BUSINESS_HOURS = {"start": 8, "end": 20, "weekdays": [0, 1, 2, 3, 4, 5]}


def is_business_hours(timezone: str = "Europe/Lisbon") -> bool:
    """
    Verifica se agora é horário permitido para envios WhatsApp.
    Args:
        timezone: timezone IANA (default: Europe/Lisbon)
    Returns:
        True se seg–sáb entre 08h00 e 20h00
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return (
        now.weekday() in BUSINESS_HOURS["weekdays"]
        and BUSINESS_HOURS["start"] <= now.hour < BUSINESS_HOURS["end"]
    )
