"""Persiste e consulta o estado de cada envio por pedido e por dispatch (formato v2 multi-disparo)."""

import fcntl
import json
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.types import DispatchType
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

SENT_FILE = Path(__file__).parent.parent.parent / "sent.json"

LOCK_TIMEOUT_SECONDS: int = 10

# Status possiveis por dispatch
VALID_STATUSES: set[str] = {
    "sent", "pending", "queued",
    "skipped_fulfilled", "skipped_reordered", "skipped_no_phone",
    "skipped_suppressed", "skipped_cooldown", "error",
}

# Flag interna para controlar se a migracao v1->v2 ja foi executada nesta sessao
_migration_done: bool = False


# ─── Funções Novas (v2) ─────────────────────────────────────────────────────


def is_dispatched(order_id: str, dispatch_type: DispatchType) -> bool:
    """
    Verifica se um disparo específico já foi enviado com sucesso para o pedido.

    Args:
        order_id: ID do pedido Shopify (string)
        dispatch_type: "D1" | "D2" | "D3" | "D4"

    Returns:
        True se dispatches[dispatch_type]["status"] == "sent"
    """
    data = _load()
    record = data.get(str(order_id), {})
    dispatches = record.get("dispatches", {})
    dispatch = dispatches.get(dispatch_type, {})
    return dispatch.get("status") == "sent"


def mark_dispatch(
    order_id: str,
    dispatch_type: DispatchType,
    status: str,
    msg_id: str = "",
    phone: str = "",
    name: str = "",
    country_code: str = "",
    language: str = "",
    **extra: str,
) -> None:
    """
    Regista um disparo no sent_tracker v2.

    Se o pedido não existir, cria a entrada completa.
    Se o pedido já existir, apenas adiciona/actualiza o dispatch.
    Se o dispatch já tiver status "sent", NÃO sobrescreve com status inferior.

    Usa file lock exclusivo (fcntl.flock) para concorrência.

    Args:
        order_id: ID do pedido Shopify
        dispatch_type: "D1" | "D2" | "D3" | "D4"
        status: um dos VALID_STATUSES
        msg_id: ID da mensagem Evolution API (opcional, apenas para "sent")
        phone: telefone normalizado (obrigatório se pedido não existir)
        name: primeiro nome (obrigatório se pedido não existir)
        country_code: ISO alpha-2 (obrigatório se pedido não existir)
        language: código idioma (obrigatório se pedido não existir)
        **extra: campos extras para o DispatchRecord (ex: segment="A", tracking_url="...")

    Raises:
        Não levanta excepções -- erros são logados
    """
    try:
        key = str(order_id)

        def _operation(data: dict) -> None:
            # Criar ou obter registo do pedido
            if key not in data:
                data[key] = {
                    "phone": phone,
                    "name": name,
                    "country_code": country_code,
                    "language": language,
                    "dispatches": {},
                }
            else:
                # Actualizar campos base se fornecidos e o pedido já existe
                record = data[key]
                if phone and not record.get("phone"):
                    record["phone"] = phone
                if name and name != "cliente" and (not record.get("name") or record["name"] == "cliente"):
                    record["name"] = name
                if country_code and not record.get("country_code"):
                    record["country_code"] = country_code
                if language and not record.get("language"):
                    record["language"] = language

            record = data[key]
            dispatches = record.setdefault("dispatches", {})

            # Não sobrescrever "sent" com status inferior
            existing = dispatches.get(dispatch_type, {})
            if existing.get("status") == "sent" and status != "sent":
                logger.info(
                    f"Pedido {order_id}/{dispatch_type} já tem status 'sent' "
                    f"— a preservar registo original."
                )
                return

            # Construir registo do dispatch
            dispatch_record: dict[str, str] = {
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if msg_id:
                dispatch_record["msg_id"] = msg_id
            # Adicionar campos extras (segment, tracking_url, etc.)
            for k, v in extra.items():
                if v:
                    dispatch_record[k] = v

            dispatches[dispatch_type] = dispatch_record

        _locked_read_write(_operation)
        logger.info(
            f"Pedido {order_id}/{dispatch_type} registado | status={status} | "
            f"phone={phone or '(existente)'}"
        )
    except Exception as e:
        logger.error(f"Erro ao registar dispatch {order_id}/{dispatch_type}: {e}")


def get_order_data(order_id: str) -> dict | None:
    """
    Retorna dados base do pedido se existir no tracker.

    Usado pelo webhook_handler para obter phone/name/country_code
    de um pedido que já teve D1 processado (evita call extra à Shopify).

    Args:
        order_id: ID do pedido Shopify

    Returns:
        dict com {phone, name, country_code, language} ou None se não existir
    """
    data = _load()
    record = data.get(str(order_id))
    if not record:
        return None
    return {
        "phone": record.get("phone", ""),
        "name": record.get("name", ""),
        "country_code": record.get("country_code", ""),
        "language": record.get("language", ""),
    }


def get_last_send_timestamp(phone: str) -> datetime | None:
    """
    Retorna timestamp do último envio bem-sucedido para este telefone.

    Percorre todos os pedidos, todos os dispatches, filtra status=="sent",
    e retorna o timestamp mais recente associado a este phone.

    Complexidade: O(n) onde n = total de dispatches. Aceitável para < 50k registos.

    Args:
        phone: telefone normalizado (apenas dígitos com DDI)

    Returns:
        datetime UTC do último envio, ou None se nunca enviado
    """
    data = _load()
    latest: datetime | None = None

    for record in data.values():
        if not isinstance(record, dict):
            continue
        if record.get("phone") != phone:
            continue
        dispatches = record.get("dispatches", {})
        for dispatch in dispatches.values():
            if not isinstance(dispatch, dict):
                continue
            if dispatch.get("status") != "sent":
                continue
            ts_str = dispatch.get("timestamp", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                # Garantir timezone-aware
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if latest is None or ts > latest:
                    latest = ts
            except (ValueError, TypeError):
                continue

    return latest


def count_sends_last_7_days(phone: str) -> int:
    """
    Conta envios bem-sucedidos nos últimos 7 dias para este telefone.

    Percorre todos os pedidos, todos os dispatches, filtra:
      - status == "sent"
      - phone == phone do pedido
      - timestamp > (now - 7 dias)

    Args:
        phone: telefone normalizado

    Returns:
        inteiro >= 0
    """
    data = _load()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    count = 0

    for record in data.values():
        if not isinstance(record, dict):
            continue
        if record.get("phone") != phone:
            continue
        dispatches = record.get("dispatches", {})
        for dispatch in dispatches.values():
            if not isinstance(dispatch, dict):
                continue
            if dispatch.get("status") != "sent":
                continue
            ts_str = dispatch.get("timestamp", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    count += 1
            except (ValueError, TypeError):
                continue

    return count


def get_last_global_send_timestamp() -> str | None:
    """
    Retorna timestamp ISO do último envio global (qualquer pedido/dispatch).

    Usado pelo health check.

    Returns:
        string ISO 8601 ou None se nenhum envio registado
    """
    data = _load()
    latest_str: str | None = None
    latest_dt: datetime | None = None

    for record in data.values():
        if not isinstance(record, dict):
            continue
        dispatches = record.get("dispatches", {})
        for dispatch in dispatches.values():
            if not isinstance(dispatch, dict):
                continue
            if dispatch.get("status") != "sent":
                continue
            ts_str = dispatch.get("timestamp", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if latest_dt is None or ts > latest_dt:
                    latest_dt = ts
                    latest_str = ts_str
            except (ValueError, TypeError):
                continue

    return latest_str


# ─── Funções Legado (deprecated, backward-compatible) ────────────────────────


def is_sent(order_id: str) -> bool:
    """
    [DEPRECATED] Verifica se QUALQUER disparo foi enviado para o pedido.

    Mantido para backward compatibility com main.py.
    Internamente verifica todos os dispatches e retorna True se algum
    tem status "sent".

    Args:
        order_id: ID do pedido Shopify

    Returns:
        True se qualquer dispatch tem status "sent"
    """
    data = _load()
    record = data.get(str(order_id), {})
    dispatches = record.get("dispatches", {})
    return any(
        d.get("status") == "sent"
        for d in dispatches.values()
        if isinstance(d, dict)
    )


def mark(
    order_id: str,
    phone: str,
    name: str,
    segment: str,
    language: str,
    status: str,
) -> None:
    """
    [DEPRECATED] Regista envio no formato legado.

    Mantido para backward compatibility com message_handler.py.
    Internamente chama mark_dispatch com dispatch_type="D4".

    Args:
        order_id: ID do pedido
        phone: telefone normalizado
        name: primeiro nome
        segment: "A_B" | "C" | "-"
        language: "pt" | "es" | "fr" | "en" | "-"
        status: "sent" | "no_phone_skip" | "already_sent_skip" | "error"
    """
    # Mapear status legado para status v2
    status_map = {
        "already_sent_skip": "skipped_suppressed",
        "no_phone_skip": "skipped_no_phone",
    }
    v2_status = status_map.get(status, status)

    extra_kwargs: dict[str, str] = {}
    if segment and segment != "-":
        extra_kwargs["segment"] = segment

    mark_dispatch(
        order_id=order_id,
        dispatch_type="D4",
        status=v2_status,
        phone=phone,
        name=name,
        language=language,
        **extra_kwargs,
    )


# ─── Migração v1 → v2 ───────────────────────────────────────────────────────


def _migrate_v1_to_v2(data: dict) -> dict:
    """
    Migra registos do formato v1 (actual) para v2 (multi-disparo).

    Detecção: um registo v1 NÃO tem chave "dispatches".
    Um registo v2 TEM chave "dispatches".

    Regras de migração:
      1. Todo registo v1 é tratado como D4 (único disparo que existia)
      2. "segment" move para dentro de dispatches.D4
      3. "status" move para dentro de dispatches.D4
      4. "timestamp" move para dentro de dispatches.D4
      5. "country_code" é preservado ou default "PT"
      6. "language" é preservado

    Args:
        data: dict do sent.json (pode ter mix de v1 e v2)

    Returns:
        dict completamente em formato v2
    """
    migrated_count = 0

    for order_id, record in data.items():
        if not isinstance(record, dict):
            continue

        # Já é formato v2 -- tem "dispatches"
        if "dispatches" in record:
            continue

        # Formato v1 detectado -- migrar
        migrated_count += 1

        v1_status = record.get("status", "error")
        v1_timestamp = record.get("timestamp", "")
        v1_segment = record.get("segment", "")
        v1_phone = record.get("phone", "")
        v1_name = record.get("name", "")
        v1_language = record.get("language", "")

        # Construir dispatch record D4
        dispatch_record: dict[str, str] = {
            "status": v1_status,
            "timestamp": v1_timestamp,
        }
        if v1_segment and v1_segment != "-":
            dispatch_record["segment"] = v1_segment

        # Construir registo v2
        data[order_id] = {
            "phone": v1_phone,
            "name": v1_name,
            "country_code": "PT",
            "language": v1_language if v1_language and v1_language != "-" else "",
            "dispatches": {
                "D4": dispatch_record,
            },
        }

    if migrated_count > 0:
        logger.info(f"Migração v1→v2: {migrated_count} registos migrados")

    return data


# ─── I/O com File Locking ────────────────────────────────────────────────────


def _load() -> dict:
    """
    Lê sent.json com file lock partilhado (LOCK_SH).

    Na primeira leitura, detecta registos v1 e executa migração automática.
    Após migração, salva o ficheiro em formato v2.

    Returns:
        dict em formato v2 (todos os registos com "dispatches")
    """
    global _migration_done

    if not SENT_FILE.exists():
        return {}

    try:
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            _acquire_lock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except json.JSONDecodeError:
        logger.warning("sent.json corrompido — a iniciar com estado vazio")
        return {}
    except Exception as e:
        logger.error(f"Erro ao ler sent.json: {e}")
        return {}

    # Migrar v1 → v2 se necessário (uma vez por sessão)
    if not _migration_done:
        needs_migration = any(
            isinstance(r, dict) and "dispatches" not in r
            for r in data.values()
        )
        if needs_migration:
            data = _migrate_v1_to_v2(data)
            _save(data)
            logger.info("Migração v1→v2 concluída e salva em disco")
        _migration_done = True

    return data


def _save(data: dict) -> None:
    """
    Escreve sent.json com file lock exclusivo (LOCK_EX).

    Args:
        data: dict em formato v2
    """
    try:
        SENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            _acquire_lock(f, fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2, ensure_ascii=False)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Erro ao escrever sent.json: {e}")


def _locked_read_write(operation_fn) -> None:
    """
    Padrão de leitura/escrita atómica com file lock exclusivo.

    Abre o ficheiro, adquire lock exclusivo, lê, executa a operação
    (que modifica data in-place), e escreve de volta.

    Args:
        operation_fn: callable que recebe data (dict) e modifica in-place
    """
    SENT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Garantir que o ficheiro existe
    if not SENT_FILE.exists():
        SENT_FILE.write_text("{}", encoding="utf-8")

    with open(SENT_FILE, "r+", encoding="utf-8") as f:
        _acquire_lock(f, fcntl.LOCK_EX)
        try:
            content = f.read()
            data = json.loads(content) if content.strip() else {}

            # Migrar se necessário
            global _migration_done
            if not _migration_done:
                needs_migration = any(
                    isinstance(r, dict) and "dispatches" not in r
                    for r in data.values()
                )
                if needs_migration:
                    data = _migrate_v1_to_v2(data)
                    logger.info("Migração v1→v2 executada durante write")
                _migration_done = True

            operation_fn(data)

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _acquire_lock(file_handle, lock_type: int) -> None:
    """
    Adquire file lock com timeout usando signal.alarm.

    Args:
        file_handle: file object aberto
        lock_type: fcntl.LOCK_EX (exclusivo) ou fcntl.LOCK_SH (partilhado)

    Raises:
        TimeoutError: se o lock não for adquirido em LOCK_TIMEOUT_SECONDS
    """
    def _timeout_handler(signum, frame):
        raise TimeoutError(
            f"File lock timeout ({LOCK_TIMEOUT_SECONDS}s) em {SENT_FILE}"
        )

    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(LOCK_TIMEOUT_SECONDS)
    try:
        fcntl.flock(file_handle, lock_type)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
