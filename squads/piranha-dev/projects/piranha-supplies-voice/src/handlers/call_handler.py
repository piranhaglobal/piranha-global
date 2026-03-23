"""Orquestra o fluxo completo por checkout: idioma → prompt → Ultravox → Twilio → tracker."""

import threading
from datetime import datetime, timezone

from src.clients.twilio import TwilioClient
from src.clients.ultravox import UltravoxClient
from src.prompts.feedback_agent import build_system_prompt
from src.utils import call_tracker
from src.utils.language_detector import get_language, get_ultravox_hint, get_voice_for_language
from src.utils.logger import setup_logger
from src.utils.product_formatter import format_products_for_voice
from src.utils.schedule_checker import is_calling_hours

logger = setup_logger(__name__)

# Mapeamento em memória partilhado com o webhook_handler.
# Chave: twilio call_sid  |  Valor: dict com joinUrl, callId, evento
# Acesso thread-safe via _sessions_lock
active_sessions: dict[str, dict] = {}
_sessions_lock = threading.Lock()

# Países da União Europeia — único território autorizado para chamadas
_EU_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
}

# --- Helpers de formatação por idioma ---

_UNITS_PT = [
    "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete",
    "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quinze",
    "dezasseis", "dezassete", "dezoito", "dezanove",
]
_TENS_PT = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
_HUNDREDS_PT = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
_MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
_MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _number_to_pt(n: int) -> str:
    """Converte inteiro não-negativo para palavras em português europeu."""
    if n == 0:
        return "zero"
    if n == 100:
        return "cem"
    parts = []
    if n >= 1000:
        thousands = n // 1000
        remainder = n % 1000
        parts.append("mil" if thousands == 1 else f"{_number_to_pt(thousands)} mil")
        if remainder > 0:
            parts.append(_number_to_pt(remainder))
        return " e ".join(parts)
    if n >= 100:
        h = n // 100
        remainder = n % 100
        parts.append(_HUNDREDS_PT[h])
        if remainder > 0:
            parts.append(_number_to_pt(remainder))
        return " e ".join(parts)
    if n >= 20:
        t = n // 10
        u = n % 10
        return _TENS_PT[t] if u == 0 else f"{_TENS_PT[t]} e {_UNITS_PT[u]}"
    return _UNITS_PT[n]


def _format_value(price_str: str, language: str) -> str:
    """Formata valor monetário de acordo com o idioma."""
    try:
        amount = float(str(price_str).replace(",", "."))
        euros = int(amount)
        cents = round((amount - euros) * 100)
        if language == "pt":
            result = f"{_number_to_pt(euros)} euros"
            if cents > 0:
                result += f" e {_number_to_pt(cents)} cêntimos"
            return result
        if language == "es":
            result = f"{euros} euros"
            if cents > 0:
                result += f" y {cents} céntimos"
            return result
        if language == "fr":
            result = f"{euros} euros"
            if cents > 0:
                result += f" et {cents} centimes"
            return result
        # en
        result = f"{euros} euros"
        if cents > 0:
            result += f" and {cents} cents"
        return result
    except (ValueError, TypeError):
        return str(price_str)


def _format_date(date_str: str, language: str) -> str:
    """Formata data ISO 8601 de forma natural para o idioma."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        day = dt.day
        year = dt.year
        if language == "pt":
            return f"{_number_to_pt(day)} de {_MONTHS_PT[dt.month - 1]} de {_number_to_pt(year)}"
        if language == "es":
            return f"{day} de {_MONTHS_ES[dt.month - 1]} de {year}"
        if language == "fr":
            return f"{day} {_MONTHS_FR[dt.month - 1]} {year}"
        # en
        return f"{_MONTHS_EN[dt.month - 1]} {day}, {year}"
    except (ValueError, AttributeError):
        return date_str


def _format_days(date_str: str, language: str) -> str:
    """Calcula dias desde a data e formata para o idioma."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        days = max(0, (datetime.now(timezone.utc) - dt).days)
        if language == "pt":
            return _number_to_pt(days)
        return str(days)
    except (ValueError, AttributeError):
        return "7"


def _format_products(products: list[dict], language: str = "pt") -> str:
    """Converte produtos em descrição natural para voz no idioma indicado."""
    return format_products_for_voice(products, language)


# --- Lógica principal ---

def process_checkouts(checkouts: list[dict]) -> None:
    """
    Processa checkouts elegíveis de forma SEQUENCIAL.

    Fluxo:
      1. Processa primeiro os leads de segunda tentativa (retry) cujo dia chegou.
      2. Processa os novos checkouts do Shopify.

    Para cada lead:
      - Verifica janela de chamadas NO TIMEZONE DO PAÍS DE DESTINO.
      - Filtra países fora da União Europeia.
      - Nunca liga ao mesmo lead duas vezes (exceto retry agendado).

    Args:
        checkouts: lista de dicts retornados por ShopifyClient (novos leads)
    """
    from datetime import date
    today_str = date.today().isoformat()

    # 1. Retries: leads que não atenderam na 1.ª tentativa e hoje é o dia agendado
    retry_leads = call_tracker.get_retry_due(today_str)
    if retry_leads:
        logger.info(f"A processar {len(retry_leads)} lead(s) de segunda tentativa (retry)")
        _process_lead_list(retry_leads, is_retry=True)

    # 2. Novos leads do Shopify
    if not checkouts:
        logger.info("Nenhum checkout novo elegível para ligar hoje.")
        return

    logger.info(f"A iniciar processamento de {len(checkouts)} checkout(s) novo(s)")
    _process_lead_list(checkouts, is_retry=False)


def _process_lead_list(checkouts: list[dict], is_retry: bool) -> None:
    """
    Itera sobre uma lista de checkouts e processa cada ligação.

    Args:
        checkouts: lista de dicts com dados do lead
        is_retry: True = segunda tentativa (bypass ao is_called check)
    """
    for checkout in checkouts:
        country = checkout.get("country_code", "PT")

        # Verificar janela de chamadas no timezone do país de destino
        if not is_calling_hours(country):
            logger.info(
                f"Fora da janela de chamadas para {country}. "
                "A suspender processamento."
            )
            break

        # Filtrar países fora da UE
        if country not in _EU_COUNTRIES:
            logger.info(f"Skip: país {country!r} fora da União Europeia — checkout {checkout['id']}")
            continue

        # Para novos leads: verificar se já foi contactado
        if not is_retry and call_tracker.is_called(checkout["id"]):
            logger.info(f"Skip: checkout {checkout['id']} já foi contactado anteriormente.")
            continue

        call_done = threading.Event()
        status = process_single(checkout, call_done)
        logger.info(f"Checkout {checkout['id']} → {status} (tentativa={'2' if is_retry else '1'})")

        if status == "called":
            logger.info("A aguardar fim da ligação antes de avançar...")
            call_done.wait()
            logger.info("Ligação terminada. A avançar para o próximo lead.")


def process_single(checkout: dict, call_done: threading.Event) -> str:
    """
    Processa um único checkout: idioma → prompt → Ultravox → Twilio → tracker.
    Args:
        checkout: dict com id, phone, name, country_code, products, total_price, created_at
        call_done: evento ativado quando o webhook receber call.hangup
    Returns:
        "called" | "already_called_skip" | "error"
    """
    checkout_id = checkout["id"]
    phone = checkout["phone"]

    try:
        context = _build_call_context(checkout)

        existing_attempts = call_tracker.get_attempts(checkout_id)
        attempts = existing_attempts + 1

        ultravox = UltravoxClient()
        session = ultravox.create_call(
            system_prompt=context["system_prompt"],
            language_hint=context["language_hint"],
            voice=context["voice"],
        )
        join_url = session["joinUrl"]
        ultravox_call_id = session["callId"]

        # Regista sessão com chave temporária (checkout_id) ANTES de disparar a
        # chamada Twilio — evita race condition onde o Twilio invoca o webhook
        # TwiML antes de active_sessions ter o call_sid real.
        _tmp_key = f"pending-{checkout_id}"
        with _sessions_lock:
            active_sessions[_tmp_key] = {
                "join_url": join_url,
                "ultravox_call_id": ultravox_call_id,
                "call_done_event": call_done,
            }

        twilio = TwilioClient()
        call_data = twilio.make_call(phone, twilio.build_twiml_url(), twilio.build_status_callback_url())
        call_sid = call_data.get("sid", "")

        # Migra para a chave real (call_sid) assim que temos o SID
        with _sessions_lock:
            active_sessions[call_sid] = active_sessions.pop(_tmp_key)

        call_tracker.mark(
            checkout_id, phone, checkout["name"], "called",
            call_sid, ultravox_call_id,
            attempts=attempts, checkout_data=checkout,
        )

        logger.info(
            f"Ligação iniciada | checkout={checkout_id} | phone={phone} "
            f"| lang={context['language']} | twilio_sid={call_sid}"
        )
        return "called"

    except Exception as e:
        logger.error(f"Erro ao processar checkout {checkout_id}: {e}")
        call_tracker.mark(checkout_id, phone, checkout["name"], "error")
        return "error"


def _build_call_context(checkout: dict) -> dict:
    """
    Monta o contexto da ligação: idioma, voz, prompt com variáveis preenchidas.
    """
    language = get_language(checkout["country_code"])
    voice = get_voice_for_language(language)
    language_hint = get_ultravox_hint(language)
    created_at = checkout.get("created_at", "")

    system_prompt = build_system_prompt(
        lead_name=checkout["name"],
        cart_products=_format_products(checkout["products"], language),
        cart_value=_format_value(checkout["total_price"], language),
        abandon_date=_format_date(created_at, language),
        days_since_abandon=_format_days(created_at, language),
        language=language,
    )

    return {
        "language": language,
        "voice": voice,
        "language_hint": language_hint,
        "system_prompt": system_prompt,
    }
