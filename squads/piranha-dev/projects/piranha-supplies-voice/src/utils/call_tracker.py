"""Persiste e consulta o estado de cada ligação em called.json."""

import json
import threading
from datetime import datetime
from pathlib import Path

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

CALLED_FILE = Path(__file__).parent.parent.parent / "called.json"
_file_lock = threading.Lock()


def is_called(checkout_id: str) -> bool:
    """
    Verifica se o checkout já foi processado (qualquer estado).
    Inclui leads com retry pendente (no_answer_1) — esses são
    geridos separadamente por get_retry_due().
    """
    with _file_lock:
        data = _load()
    return str(checkout_id) in data


def mark(
    checkout_id: str,
    phone: str,
    name: str,
    status: str,
    provider_call_id: str | None = None,
    ultravox_call_id: str | None = None,
    attempts: int = 1,
    checkout_data: dict | None = None,
    join_url: str | None = None,
) -> None:
    """
    Registra ou atualiza uma ligação no called.json.

    Args:
        checkout_id: ID do checkout Shopify
        phone: número chamado em E.164
        name: primeiro nome do cliente
        status: "called" | "no_phone_skip" | "already_called_skip" | "error"
        provider_call_id: call_sid Twilio
        ultravox_call_id: callId Ultravox
        attempts: número da tentativa (1 ou 2)
        checkout_data: dict completo do checkout — necessário para agendar retry
        join_url: WebSocket URL do Ultravox — guardado para recuperação após reinício
    """
    with _file_lock:
        data = _load()
        data[str(checkout_id)] = {
            "phone": phone,
            "name": name,
            "status": status,
            "attempts": attempts,
            "provider_call_id": provider_call_id,
            "ultravox_call_id": ultravox_call_id,
            "join_url": join_url,
            "timestamp": datetime.utcnow().isoformat(),
            "checkout_data": checkout_data,
        }
        _save(data)
    logger.info(f"Checkout {checkout_id} registado | status={status} | phone={phone} | tentativa={attempts}")


def update_status(provider_call_id: str, new_status: str) -> None:
    """
    Atualiza o status de uma ligação existente pelo provider_call_id (Twilio call_sid).
    Usado para marcar chamadas como "completed".
    Para no-answer, usar mark_for_retry() ou mark_no_answer_final().
    """
    with _file_lock:
        data = _load()
        for checkout_id, record in data.items():
            if record.get("provider_call_id") == provider_call_id:
                record["status"] = new_status
                record["completed_at"] = datetime.utcnow().isoformat()
                _save(data)
                logger.info(f"Status atualizado | provider_id={provider_call_id} | novo status={new_status}")
                return
    logger.warning(f"provider_call_id não encontrado no tracker: {provider_call_id}")


def mark_for_retry(checkout_id: str, retry_date: str) -> None:
    """
    Agenda uma segunda tentativa para um lead que não atendeu.
    Define status="no_answer_1" e retry_date (formato YYYY-MM-DD).

    O lead será processado pelo get_retry_due() no dia agendado.
    Fins de semana são automaticamente deslocados para segunda-feira
    pela lógica de next_business_day() em schedule_checker.
    """
    with _file_lock:
        data = _load()
        cid = str(checkout_id)
        if cid in data:
            data[cid]["status"] = "no_answer_1"
            data[cid]["retry_date"] = retry_date
            data[cid]["completed_at"] = datetime.utcnow().isoformat()
            _save(data)
    logger.info(f"Retry agendado | checkout={checkout_id} | data={retry_date}")


def mark_no_answer_final(checkout_id: str) -> None:
    """
    Encerra definitivamente um lead após a 2.ª tentativa sem resposta.
    Nunca voltará a ser contactado.
    """
    with _file_lock:
        data = _load()
        cid = str(checkout_id)
        if cid in data:
            data[cid]["status"] = "no_answer_final"
            data[cid]["completed_at"] = datetime.utcnow().isoformat()
            _save(data)
    logger.info(f"Sem contacto definitivo | checkout={checkout_id}")


def get_retry_due(today_str: str) -> list[dict]:
    """
    Retorna a lista de checkout_data para leads com retry agendado para hoje ou antes.

    Args:
        today_str: data de hoje em formato "YYYY-MM-DD"
    Returns:
        lista de dicts checkout prontos para segunda tentativa
    """
    with _file_lock:
        data = _load()
    results = []
    for checkout_id, record in data.items():
        if (
            record.get("status") == "no_answer_1"
            and record.get("retry_date", "9999-99-99") <= today_str
            and record.get("checkout_data")
        ):
            results.append(record["checkout_data"])
    return results


def get_join_url_by_provider_id(provider_call_id: str) -> str | None:
    """
    Retorna o join_url Ultravox guardado para um dado call_sid Twilio.
    Usado pelo TwiML handler para recuperar a sessão após reinício do container.
    """
    with _file_lock:
        data = _load()
    for record in data.values():
        if record.get("provider_call_id") == provider_call_id:
            return record.get("join_url")
    return None


def get_record_by_provider_id(provider_call_id: str) -> tuple[str, dict] | None:
    """
    Retorna (checkout_id, record) para um dado provider_call_id (Twilio call_sid).
    Usado pelo webhook para decidir se agenda retry ou fecha definitivamente.
    """
    with _file_lock:
        data = _load()
    for checkout_id, record in data.items():
        if record.get("provider_call_id") == provider_call_id:
            return checkout_id, record
    return None


def get_attempts(checkout_id: str) -> int:
    """Retorna o número de tentativas já realizadas para este checkout."""
    with _file_lock:
        data = _load()
    return data.get(str(checkout_id), {}).get("attempts", 0)


def log_result(
    provider_call_id: str,
    motivo_principal: str,
    sub_motivo: str,
    resultado: str,
) -> None:
    """
    Actualiza o registo com o resultado reportado pelo agente via logCallResult.
    Procura por provider_call_id (Twilio call_sid).
    """
    _write_call_result(
        field="provider_call_id",
        value=provider_call_id,
        motivo_principal=motivo_principal,
        sub_motivo=sub_motivo,
        resultado=resultado,
    )


def log_result_by_ultravox_id(
    ultravox_call_id: str,
    motivo_principal: str,
    sub_motivo: str,
    resultado: str,
) -> None:
    """
    Actualiza o registo com o resultado via logCallResult.
    Procura por ultravox_call_id — útil quando a sessão Twilio já foi removida.
    """
    _write_call_result(
        field="ultravox_call_id",
        value=ultravox_call_id,
        motivo_principal=motivo_principal,
        sub_motivo=sub_motivo,
        resultado=resultado,
    )


def _write_call_result(
    field: str,
    value: str,
    motivo_principal: str,
    sub_motivo: str,
    resultado: str,
) -> None:
    with _file_lock:
        data = _load()
        for checkout_id, record in data.items():
            if record.get(field) == value:
                record["call_result"] = {
                    "motivo_principal": motivo_principal,
                    "sub_motivo": sub_motivo,
                    "resultado": resultado,
                    "logged_at": datetime.utcnow().isoformat(),
                }
                _save(data)
                logger.info(
                    f"logCallResult registado | {field}={value} "
                    f"| resultado={resultado} | motivo={motivo_principal}"
                )
                return
    logger.warning(f"logCallResult: {field}={value!r} não encontrado no tracker")


def _load() -> dict:
    """Lê called.json. Deve ser chamada dentro de _file_lock. Retorna {} se não existir."""
    if CALLED_FILE.exists():
        try:
            return json.loads(CALLED_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("called.json corrompido — iniciando com estado vazio")
    return {}


def _save(data: dict) -> None:
    """Escreve called.json com indentação. Deve ser chamada dentro de _file_lock."""
    CALLED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
