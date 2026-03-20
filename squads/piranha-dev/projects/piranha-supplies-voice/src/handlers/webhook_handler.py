"""Servidor Flask — recebe eventos Twilio e conecta cliente ao Ultravox via TwiML."""

import threading

from flask import Flask, Response, jsonify, request

from src.handlers.call_handler import _sessions_lock, active_sessions, process_single
from src.utils import call_tracker
from src.utils.call_tracker import log_result_by_ultravox_id
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_app() -> Flask:
    """
    Cria e configura a aplicação Flask.
    Returns:
        instância configurada do Flask
    """
    app = Flask(__name__)

    @app.route("/webhook/twilio/twiml", methods=["GET", "POST"])
    def twilio_twiml() -> Response:
        """
        Retorna TwiML quando a chamada atender.
        Deve responder em menos de 2s.
        """
        call_sid = _get_form_value("CallSid")
        logger.info(f"Webhook Twilio TwiML | sid={call_sid}")

        with _sessions_lock:
            session = active_sessions.get(call_sid)

        if not session:
            logger.warning(f"TwiML sem sessão activa: {call_sid}")
            return Response(_build_twiml(""), mimetype="application/xml", status=200)

        join_url = session["join_url"]
        logger.info(f"A conectar ao Ultravox | sid={call_sid}")
        return Response(_build_twiml(join_url), mimetype="application/xml", status=200)

    @app.route("/webhook/twilio/status", methods=["POST"])
    def twilio_status() -> Response:
        """
        Recebe callbacks de estado da chamada Twilio.
        - answered: evento intermédio
        - completed/busy/failed/no-answer/canceled: evento final
        """
        call_sid = _get_form_value("CallSid")
        call_status = _get_form_value("CallStatus").lower()
        answered_by = _get_form_value("AnsweredBy")
        if answered_by:
            logger.info(f"Webhook Twilio status | sid={call_sid} | status={call_status} | answered_by={answered_by}")
        else:
            logger.info(f"Webhook Twilio status | sid={call_sid} | status={call_status}")

        if call_status in {"completed", "busy", "failed", "no-answer", "canceled"}:
            tracker_status = "completed" if call_status == "completed" else "failed"
            call_tracker.update_status(call_sid, tracker_status)
            with _sessions_lock:
                session = active_sessions.pop(call_sid, None)
            if session and session.get("call_done_event"):
                session["call_done_event"].set()

        return Response("OK", status=200)

    @app.route("/health", methods=["GET"])
    def health() -> Response:
        """Health check — confirma que o servidor está em funcionamento."""
        return Response("OK", status=200)

    @app.route("/admin/test-call", methods=["POST"])
    def admin_test_call() -> Response:
        """
        Dispara uma chamada de teste no mesmo processo do servidor.
        Necessário para que active_sessions seja partilhado corretamente.

        Body JSON:
            to_number   (str) — número destino em E.164
            name        (str) — nome do cliente fictício
            country_code (str) — ex: "PT", "ES"
            products    (list) — lista de dicts com "title" e "price"
            total_price (str) — valor total

        Exemplo:
            curl -X POST https://call.piranhasupplies.com/admin/test-call \
              -H "Content-Type: application/json" \
              -d '{"to_number":"+351912345678","name":"Sofia","country_code":"PT",
                   "products":[{"title":"Pro Blade 300mm","price":"89.90"}],
                   "total_price":"89.90"}'
        """
        data = request.get_json(silent=True) or {}
        to_number = data.get("to_number", "")
        if not to_number:
            return jsonify({"error": "to_number obrigatório"}), 400

        from datetime import datetime, timedelta, timezone as tz
        default_created_at = (datetime.now(tz.utc) - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
        checkout = {
            "id": f"test-{to_number}",
            "phone": to_number,
            "name": data.get("name", "Cliente"),
            "country_code": data.get("country_code", "PT"),
            "products": data.get("products", [{"title": "Produto Teste", "price": "99.90"}]),
            "total_price": data.get("total_price", "99.90"),
            "created_at": data.get("created_at", default_created_at),
        }

        call_done = threading.Event()

        def _run():
            process_single(checkout, call_done)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return jsonify({"status": "chamada iniciada", "to": to_number}), 202

    @app.route("/webhook/log-call-result", methods=["POST"])
    def log_call_result() -> Response:
        """
        Recebe o resultado da chamada reportado pelo agente Bruno via tool logCallResult.
        Ultravox envia o call ID no header X-UV-Call-Id.
        """
        ultravox_call_id = request.headers.get("X-UV-Call-Id", "")
        data = request.get_json(silent=True) or {}

        motivo_principal = data.get("motivo_principal", "outro")
        sub_motivo = data.get("sub_motivo", "")
        resultado = data.get("resultado", "")

        logger.info(
            f"logCallResult recebido | ultravox_id={ultravox_call_id} "
            f"| resultado={resultado} | motivo={motivo_principal}"
        )

        # Encontrar o call_sid Twilio correspondente ao ultravox_call_id
        call_sid = None
        with _sessions_lock:
            for sid, session in active_sessions.items():
                if session.get("ultravox_call_id") == ultravox_call_id:
                    call_sid = sid
                    break

        if call_sid:
            call_tracker.log_result(call_sid, motivo_principal, sub_motivo, resultado)
        else:
            # Sessão Twilio já removida — procura pelo ultravox_call_id persistido no tracker
            logger.info(f"logCallResult: sessão activa não encontrada, a usar fallback por ultravox_id={ultravox_call_id}")
            log_result_by_ultravox_id(ultravox_call_id, motivo_principal, sub_motivo, resultado)

        return jsonify({"status": "ok"}), 200

    return app


def _build_twiml(join_url: str) -> str:
    """
    Gera o XML de resposta para conectar o cliente ao WebSocket Ultravox.
    Args:
        join_url: wss://... retornado pelo UltravoxClient
    Returns:
        string XML válida para o Twilio (deve chegar em < 2s)
    """
    if not join_url:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Hangup/>"
            "</Response>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Connect><Stream url="{join_url}" /></Connect>'
        "</Response>"
    )


def _get_form_value(key: str) -> str:
    value = request.form.get(key, "")
    if value:
        return value
    return request.args.get(key, "")
