"""Servidor Flask — recebe eventos Twilio e conecta cliente ao Ultravox via TwiML."""

import threading
import time

from flask import Flask, Response, jsonify, request

# Transferências pendentes: support_call_sid → {conference_name, safe_summary, base_url, auth}
# Usado para injetar o contexto após o suporte atender (delay programático)
_pending_transfers: dict[str, dict] = {}
_pending_transfers_lock = threading.Lock()

from src.clients.twilio import TwilioClient
from src.clients.ultravox import TRANSFER_NUMBER
from src.config import Config
from src.handlers.call_handler import _sessions_lock, active_sessions, process_single
from src.utils import call_tracker
from src.utils.call_tracker import log_result_by_ultravox_id
from src.utils.logger import setup_logger
from src.utils.schedule_checker import next_business_day

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
        Fallback: se a sessão não está em memória (ex: reinício do container),
        tenta recuperar o join_url persistido no called.json.
        """
        call_sid = _get_form_value("CallSid")
        logger.info(f"Webhook Twilio TwiML | sid={call_sid}")

        with _sessions_lock:
            session = active_sessions.get(call_sid)

        if session:
            join_url = session["join_url"]
            logger.info(f"A conectar ao Ultravox | sid={call_sid}")
            return Response(_build_twiml(join_url), mimetype="application/xml", status=200)

        # Sessão não encontrada em memória — tentar recuperar do called.json
        recovered_url = call_tracker.get_join_url_by_provider_id(call_sid)
        if recovered_url:
            logger.warning(
                f"TwiML: sessão não encontrada em memória (reinício?) | sid={call_sid} "
                "— a usar join_url persistido no called.json"
            )
            return Response(_build_twiml(recovered_url), mimetype="application/xml", status=200)

        logger.error(f"TwiML: sem sessão e sem join_url persistido para sid={call_sid} — a desligar")
        return Response(_build_twiml(""), mimetype="application/xml", status=200)

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
            if call_status == "completed":
                call_tracker.update_status(call_sid, "completed")
            else:
                # Chamada não atendida — verificar tentativas para retry ou encerrar
                result = call_tracker.get_record_by_provider_id(call_sid)
                if result:
                    checkout_id, record = result
                    if record.get("attempts", 1) < 2:
                        retry_date = next_business_day().isoformat()
                        call_tracker.mark_for_retry(checkout_id, retry_date)
                        logger.info(
                            f"Retry agendado | sid={call_sid} | checkout={checkout_id} "
                            f"| data={retry_date}"
                        )
                    else:
                        call_tracker.mark_no_answer_final(checkout_id)
                        logger.info(
                            f"Lead encerrado definitivamente | sid={call_sid} | checkout={checkout_id}"
                        )
                else:
                    call_tracker.update_status(call_sid, "failed")

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

        Modo 1 — checkout_id (recomendado): busca dados reais do Shopify
            {"checkout_id": "36031105368169"}

        Modo 2 — dados manuais (fallback):
            {"to_number":"+351912345678","name":"Sofia","country_code":"PT",
             "products":[{"title":"Pro Blade 300mm","price":"89.90"}],
             "total_price":"89.90"}
        """
        data = request.get_json(silent=True) or {}

        checkout_id = data.get("checkout_id", "").strip()
        if checkout_id:
            # Modo 1: buscar checkout real do Shopify (com product info enriquecido)
            from src.clients.shopify import ShopifyClient
            from datetime import datetime, timedelta, timezone as tz

            shopify = ShopifyClient()
            raw = None
            now = datetime.now(tz.utc)
            for days_back in [14, 30, 60, 90]:
                created_at_min = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
                resp = shopify._make_request("GET", "/checkouts.json", params={
                    "status": "open", "limit": 250, "created_at_min": created_at_min,
                })
                for c in resp.get("checkouts", []):
                    if str(c.get("id", "")) == checkout_id:
                        raw = c
                        break
                if raw:
                    break

            if not raw:
                # Última tentativa sem filtro de data
                resp = shopify._make_request("GET", "/checkouts.json", params={
                    "status": "open", "limit": 250,
                })
                for c in resp.get("checkouts", []):
                    if str(c.get("id", "")) == checkout_id:
                        raw = c
                        break

            if not raw:
                return jsonify({"error": f"checkout {checkout_id} não encontrado"}), 404

            checkout = shopify._extract_contact(raw)

            # Garantir telefone (pode estar só no shipping_address)
            if not checkout["phone"]:
                shipping = raw.get("shipping_address") or raw.get("billing_address") or {}
                checkout["phone"] = shipping.get("phone", "")

            if not checkout["phone"]:
                return jsonify({"error": "checkout sem telefone — não é possível ligar"}), 422

            to_number = checkout["phone"]
            logger.info(
                f"test-call via checkout_id={checkout_id} | "
                f"phone={to_number} | produtos={len(checkout['products'])}"
            )
        else:
            # Modo 2: dados manuais passados no body
            to_number = data.get("to_number", "")
            if not to_number:
                return jsonify({"error": "checkout_id ou to_number obrigatório"}), 400

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

    @app.route("/webhook/warm-transfer", methods=["POST"])
    def warm_transfer() -> Response:
        """
        Transferência com contexto (warm transfer) via Twilio Conference.

        Fluxo:
          1. Lê o resumo da conversa enviado pelo agente Ultravox.
          2. Encontra o call_sid Twilio da chamada ativa.
          3. Liga ao número de suporte — ao atender, ouve o contexto e entra na conferência.
          4. Redireciona o cliente para a mesma conferência.
          Resultado: cliente e suporte ficam ligados em conferência com contexto partilhado.

        Body JSON (enviado pelo Ultravox):
            summary (str) — resumo da conversa e motivo da transferência
        Header:
            X-UV-Call-Id — callId Ultravox (pode estar vazio)
        """
        ultravox_call_id = request.headers.get("X-UV-Call-Id", "")
        data = request.get_json(silent=True) or {}
        summary = data.get("summary", "Transferência de chamada Piranha Supplies")

        # Encontrar o call_sid Twilio a partir da sessão ativa
        call_sid = None
        with _sessions_lock:
            if ultravox_call_id:
                for sid, session in active_sessions.items():
                    if session.get("ultravox_call_id") == ultravox_call_id:
                        call_sid = sid
                        break
            if not call_sid and len(active_sessions) == 1:
                call_sid, _ = next(iter(active_sessions.items()))

        if not call_sid:
            logger.error("Warm transfer: nenhuma sessão ativa encontrada")
            return jsonify({"error": "sessão não encontrada"}), 404

        # Nome único da conferência baseado no call_sid
        conference_name = f"piranha-wt-{call_sid[-10:]}"
        safe_summary = summary.replace("<", "").replace(">", "").replace("&", "e")[:300]

        # TwiML inicial para o suporte: silêncio enquanto aguarda o contexto vindo do backend
        # O contexto real é injetado via REST API após 2s (no endpoint /webhook/twilio/support-answer)
        support_hold_twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '<Pause length="30"/>'
            "</Response>"
        )

        # TwiML de contexto + conferência — injetado após delay de 2s
        support_context_twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say voice="alice" language="pt-PT">'
            f"Piranha Supplies. Transferência com contexto. {safe_summary}"
            f"</Say>"
            f'<Dial><Conference startConferenceOnEnter="true" endConferenceOnExit="false">'
            f"{conference_name}"
            f"</Conference></Dial>"
            "</Response>"
        )

        # TwiML para o cliente: entra na conferência (aguarda suporte)
        customer_twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Dial><Conference startConferenceOnEnter="false" endConferenceOnExit="true">'
            f"{conference_name}"
            f"</Conference></Dial>"
            "</Response>"
        )

        twilio = TwilioClient()
        status_callback_url = f"{Config.VPS_BASE_URL}/webhook/twilio/support-answer"

        # 1. Ligar ao suporte com TwiML de espera + StatusCallback para quando atender
        try:
            resp = twilio.session.post(
                f"{twilio.base_url}/Accounts/{twilio.account_sid}/Calls.json",
                data={
                    "To": TRANSFER_NUMBER,
                    "From": Config.TWILIO_FROM_NUMBER,
                    "Twiml": support_hold_twiml,
                    "StatusCallback": status_callback_url,
                    "StatusCallbackEvent": "answered",
                    "StatusCallbackMethod": "POST",
                },
                auth=twilio.auth,
            )
            resp.raise_for_status()
            support_sid = resp.json().get("sid", "")
            logger.info(f"Warm transfer: suporte ligado | sid={support_sid} | conf={conference_name}")
        except Exception as e:
            logger.error(f"Warm transfer: erro ao ligar suporte: {e}")
            return jsonify({"error": "falha ao contactar suporte"}), 500

        # Guardar contexto para injetar quando o suporte atender
        with _pending_transfers_lock:
            _pending_transfers[support_sid] = {
                "conference_name": conference_name,
                "context_twiml": support_context_twiml,
                "base_url": twilio.base_url,
                "account_sid": twilio.account_sid,
                "auth": twilio.auth,
            }

        # 2. Redirecionar o cliente para a conferência
        try:
            upd = twilio.session.post(
                f"{twilio.base_url}/Accounts/{twilio.account_sid}/Calls/{call_sid}.json",
                data={"Twiml": customer_twiml},
                auth=twilio.auth,
            )
            upd.raise_for_status()
            logger.info(f"Warm transfer: cliente redirecionado | sid={call_sid} | conf={conference_name}")
        except Exception as e:
            logger.error(f"Warm transfer: erro ao redirecionar cliente: {e}")
            return jsonify({"error": "falha ao transferir cliente"}), 500

        return jsonify({"status": "transferência iniciada", "conference": conference_name}), 200

    @app.route("/webhook/twilio/support-answer", methods=["POST"])
    def support_answer() -> Response:
        """
        Recebe o StatusCallback do Twilio quando o suporte atende a chamada.
        Aguarda 2 segundos e injeta o contexto + redireciona para conferência.
        O delay é programático (thread) — garante que a pessoa tem tempo
        de colocar o telefone no ouvido antes de ouvir o briefing.
        """
        call_sid = request.form.get("CallSid", "")
        call_status = request.form.get("CallStatus", "")

        if call_status != "in-progress":
            return ("", 204)

        with _pending_transfers_lock:
            transfer = _pending_transfers.pop(call_sid, None)

        if not transfer:
            logger.warning(f"support-answer: sem transferência pendente para sid={call_sid}")
            return ("", 204)

        logger.info(f"Warm transfer: suporte atendeu | sid={call_sid} | a aguardar 2s antes do contexto")

        def _inject_context():
            time.sleep(2)
            try:
                import requests as _req
                r = _req.post(
                    f"{transfer['base_url']}/Accounts/{transfer['account_sid']}/Calls/{call_sid}.json",
                    data={"Twiml": transfer["context_twiml"]},
                    auth=transfer["auth"],
                    timeout=10,
                )
                r.raise_for_status()
                logger.info(f"Warm transfer: contexto injetado após 2s | sid={call_sid} | conf={transfer['conference_name']}")
            except Exception as e:
                logger.error(f"Warm transfer: erro ao injetar contexto | sid={call_sid} | {e}")

        threading.Thread(target=_inject_context, daemon=True).start()
        return ("", 204)

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
        # Fallback 1: header vazio mas há exatamente 1 sessão ativa (chamadas são sequenciais)
        call_sid = None
        resolved_ultravox_id = ultravox_call_id
        with _sessions_lock:
            if ultravox_call_id:
                for sid, session in active_sessions.items():
                    if session.get("ultravox_call_id") == ultravox_call_id:
                        call_sid = sid
                        break
            if not call_sid and len(active_sessions) == 1:
                call_sid, session = next(iter(active_sessions.items()))
                resolved_ultravox_id = session.get("ultravox_call_id", "")
                logger.info(
                    f"logCallResult: header X-UV-Call-Id vazio — "
                    f"a usar sessão única ativa | sid={call_sid} | ultravox_id={resolved_ultravox_id}"
                )

        if call_sid:
            call_tracker.log_result(call_sid, motivo_principal, sub_motivo, resultado)
        else:
            # Fallback 2: sessão já removida — procura pelo ultravox_call_id no tracker
            logger.info(f"logCallResult: sem sessão ativa, a usar fallback por ultravox_id={resolved_ultravox_id}")
            log_result_by_ultravox_id(resolved_ultravox_id, motivo_principal, sub_motivo, resultado)

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
