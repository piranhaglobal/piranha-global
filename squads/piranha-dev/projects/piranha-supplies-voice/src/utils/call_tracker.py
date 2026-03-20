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
    Verifica se o checkout já foi processado.
    Args:
        checkout_id: ID do checkout Shopify
    Returns:
        True se já existir registro
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
) -> None:
    """
    Registra uma ligação no called.json.
    Args:
        checkout_id: ID do checkout Shopify
        phone: número chamado em E.164
        name: primeiro nome do cliente
        status: "called" | "no_phone_skip" | "already_called_skip" | "error"
        provider_call_id: call_sid Twilio
        ultravox_call_id: callId Ultravox (para lookup do logCallResult)
    """
    with _file_lock:
        data = _load()
        data[str(checkout_id)] = {
            "phone": phone,
            "name": name,
            "status": status,
            "provider_call_id": provider_call_id,
            "ultravox_call_id": ultravox_call_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        _save(data)
    logger.info(f"Checkout {checkout_id} registado | status={status} | phone={phone}")


def update_status(provider_call_id: str, new_status: str) -> None:
    """
    Atualiza o status de uma ligação existente pelo provider_call_id (Twilio call_sid).
    Args:
        provider_call_id: call_sid Twilio
        new_status: "completed" | "no_answer" | "failed"
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


def log_result(
    provider_call_id: str,
    motivo_principal: str,
    sub_motivo: str,
    resultado: str,
) -> None:
    """
    Actualiza o registo de uma chamada com o resultado reportado pelo agente via logCallResult.
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
    Actualiza o registo de uma chamada com o resultado reportado pelo agente via logCallResult.
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
