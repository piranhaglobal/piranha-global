"""Servidor Flask — recebe eventos Twilio e conecta cliente ao Ultravox via TwiML."""

import threading

from flask import Flask, Response, jsonify, request

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

    @app.route("/admin/calls/<checkout_id>/transcript", methods=["GET"])
    def admin_transcript(checkout_id: str) -> Response:
        """
        Retorna a transcrição de uma chamada como JSON.
        Chamado via AJAX pelo dashboard para popular o modal.
        """
        import json
        from pathlib import Path
        from src.clients.ultravox import UltravoxClient

        called_file = Path(__file__).parent.parent.parent / "called.json"
        try:
            data = json.loads(called_file.read_text(encoding="utf-8")) if called_file.exists() else {}
        except Exception:
            return jsonify({"error": "called.json ilegível"}), 500

        record = data.get(str(checkout_id))
        if not record:
            return jsonify({"error": "checkout não encontrado"}), 404

        ultravox_call_id = record.get("ultravox_call_id")
        if not ultravox_call_id:
            return jsonify({"error": "sem ultravox_call_id — chamada não iniciada"}), 404

        try:
            uv = UltravoxClient()
            messages = uv.get_transcript(ultravox_call_id)
            return jsonify({
                "checkout_id": checkout_id,
                "name": record.get("name", "—"),
                "phone": record.get("phone", "—"),
                "status": record.get("status", "—"),
                "ultravox_call_id": ultravox_call_id,
                "messages": messages,
            })
        except Exception as e:
            logger.error(f"Erro ao buscar transcrição Ultravox: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/calls", methods=["GET"])
    def admin_calls() -> Response:
        """
        Dashboard HTML de chamadas — lista todas as interações com leads.
        Acesso: https://call.piranhasupplies.com/admin/calls
        """
        import json
        from pathlib import Path
        from datetime import datetime

        called_file = Path(__file__).parent.parent.parent / "called.json"
        try:
            data = json.loads(called_file.read_text(encoding="utf-8")) if called_file.exists() else {}
        except Exception:
            data = {}

        # Ordenar por timestamp desc
        records = sorted(data.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)

        # Totais por status
        counts = {}
        for _, r in records:
            s = r.get("status", "?")
            counts[s] = counts.get(s, 0) + 1

        def fmt_dt(iso):
            if not iso:
                return "—"
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return iso[:16]

        def fmt_dur(start, end):
            if not start or not end:
                return "—"
            try:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                secs = int((e - s).total_seconds())
                if secs < 0:
                    return "—"
                m, sec = divmod(secs, 60)
                return f"{m}m{sec:02d}s"
            except Exception:
                return "—"

        _status_cfg = {
            "completed":          ("#22c55e", "#f0fdf4", "Concluída"),
            "called":             ("#f59e0b", "#fffbeb", "Em curso"),
            "no_answer_1":        ("#a855f7", "#faf5ff", "Sem resp. (1ª)"),
            "no_answer_final":    ("#ef4444", "#fef2f2", "Sem resp. final"),
            "error":              ("#dc2626", "#fef2f2", "Erro"),
            "already_called_skip":("#6b7280", "#f9fafb", "Ignorado"),
        }

        def badge(status):
            color, bg, label = _status_cfg.get(status, ("#6b7280", "#f9fafb", status))
            return f'<span style="background:{bg};color:{color};border:1px solid {color};padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{label}</span>'

        # Construir linhas da tabela
        rows_html = ""
        for checkout_id, r in records:
            cd = r.get("checkout_data") or {}
            products = cd.get("products") or []
            prod_names = "<br>".join(
                f'<span style="font-size:11px">{p.get("title","?")[:40]}</span>'
                for p in products[:3]
            )
            total = f'{cd.get("total_price","?")}&nbsp;€' if cd else "—"
            result = r.get("call_result") or {}
            resultado_html = ""
            if result:
                res = result.get("resultado", "")
                mot = result.get("motivo_principal", "")
                resultado_html = f'<div style="margin-top:4px;font-size:11px;color:#6b7280">{res} · {mot}</div>'

            has_transcript = bool(r.get("ultravox_call_id"))
            transcript_btn = (
                f'<button onclick="openTranscript(\'{checkout_id}\',\'{r.get("name","—")}\',\'{r.get("phone","—")}\')" '
                f'style="margin-top:6px;background:#3b82f6;color:white;border:none;border-radius:6px;'
                f'padding:3px 10px;font-size:11px;cursor:pointer">💬 Ver conversa</button>'
            ) if has_transcript else ""

            rows_html += f"""
            <tr>
              <td style="font-family:monospace;font-size:11px;color:#6b7280">{checkout_id}</td>
              <td><strong>{r.get("name","—")}</strong><br><span style="font-size:11px;color:#6b7280">{r.get("phone","—")}</span></td>
              <td style="font-size:11px">{cd.get("country_code","?")}</td>
              <td>{prod_names}</td>
              <td style="text-align:right;font-weight:600">{total}</td>
              <td style="font-size:11px">{fmt_dt(cd.get("created_at",""))}</td>
              <td style="font-size:11px">{fmt_dt(r.get("timestamp",""))}</td>
              <td style="font-size:11px;text-align:center">{fmt_dur(r.get("timestamp"), r.get("completed_at"))}</td>
              <td style="text-align:center">{r.get("attempts",1)}</td>
              <td>{badge(r.get("status","?"))}{resultado_html}{transcript_btn}</td>
            </tr>"""

        # Cards de resumo
        summary_cards = ""
        for status, (color, bg, label) in _status_cfg.items():
            count = counts.get(status, 0)
            if count == 0:
                continue
            summary_cards += f"""
            <div style="background:{bg};border:1px solid {color}30;border-radius:8px;padding:12px 20px;min-width:130px">
              <div style="font-size:11px;color:{color};font-weight:600;text-transform:uppercase">{label}</div>
              <div style="font-size:28px;font-weight:700;color:{color}">{count}</div>
            </div>"""

        total_all = len(records)
        now_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")

        html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Piranha Supplies Voice — Log de Chamadas</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0 }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f8fafc; color:#1e293b; }}
    .header {{ background:#0f172a; color:white; padding:20px 32px; display:flex; justify-content:space-between; align-items:center }}
    .header h1 {{ font-size:18px; font-weight:600 }}
    .header span {{ font-size:12px; color:#94a3b8 }}
    .container {{ padding:24px 32px }}
    .summary {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px }}
    .total-card {{ background:white;border:1px solid #e2e8f0;border-radius:8px;padding:12px 20px;min-width:130px }}
    .total-card .n {{ font-size:28px;font-weight:700;color:#0f172a }}
    .total-card .l {{ font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase }}
    table {{ width:100%; border-collapse:collapse; background:white; border-radius:10px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.08) }}
    th {{ background:#f1f5f9; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#64748b; padding:10px 12px; text-align:left; border-bottom:1px solid #e2e8f0 }}
    td {{ padding:10px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top }}
    tr:last-child td {{ border-bottom:none }}
    tr:hover td {{ background:#f8fafc }}
    .refresh {{ font-size:11px; color:#64748b; margin-bottom:16px }}
    a {{ color:#3b82f6; text-decoration:none }}
  </style>
  <meta http-equiv="refresh" content="60">
</head>
<body>
  <div class="header">
    <h1>🦈 Piranha Supplies Voice — Log de Chamadas</h1>
    <span>Atualizado: {now_str} · auto-refresh 60s</span>
  </div>
  <div class="container">
    <div class="summary">
      <div class="total-card">
        <div class="n">{total_all}</div>
        <div class="l">Total</div>
      </div>
      {summary_cards}
    </div>
    <p class="refresh">
      <a href="/admin/calls">⟳ Atualizar agora</a>
    </p>
    <table>
      <thead>
        <tr>
          <th>Checkout ID</th>
          <th>Cliente</th>
          <th>País</th>
          <th>Produtos</th>
          <th style="text-align:right">Total</th>
          <th>Abandono</th>
          <th>Chamada</th>
          <th style="text-align:center">Duração</th>
          <th style="text-align:center">Tent.</th>
          <th>Status / Resultado</th>
        </tr>
      </thead>
      <tbody>
        {rows_html if rows_html else '<tr><td colspan="10" style="text-align:center;color:#94a3b8;padding:40px">Nenhuma chamada registada ainda.</td></tr>'}
      </tbody>
    </table>
  </div>

  <!-- MODAL TRANSCRIÇÃO -->
  <div id="modal-overlay" onclick="closeModal()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;align-items:center;justify-content:center"></div>
  <div id="modal" style="display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:101;background:white;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:min(680px,95vw);max-height:85vh;overflow:hidden;flex-direction:column">
    <div style="padding:16px 20px;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center">
      <div>
        <div id="modal-title" style="font-weight:600;font-size:15px"></div>
        <div id="modal-sub" style="font-size:12px;color:#64748b;margin-top:2px"></div>
      </div>
      <button onclick="closeModal()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#64748b;line-height:1">✕</button>
    </div>
    <div id="modal-body" style="overflow-y:auto;padding:20px;flex:1;max-height:calc(85vh - 70px)">
      <div id="modal-loading" style="text-align:center;padding:40px;color:#94a3b8">A carregar transcrição...</div>
      <div id="modal-messages" style="display:none;display:flex;flex-direction:column;gap:12px"></div>
      <div id="modal-error" style="display:none;color:#ef4444;text-align:center;padding:40px"></div>
    </div>
  </div>

  <script>
    function openTranscript(checkoutId, name, phone) {{
      document.getElementById('modal-title').textContent = name + '  ·  ' + phone;
      document.getElementById('modal-sub').textContent = 'Checkout #' + checkoutId;
      document.getElementById('modal-loading').style.display = 'block';
      document.getElementById('modal-messages').style.display = 'none';
      document.getElementById('modal-messages').innerHTML = '';
      document.getElementById('modal-error').style.display = 'none';
      document.getElementById('modal-overlay').style.display = 'block';
      document.getElementById('modal').style.display = 'flex';

      fetch('/admin/calls/' + checkoutId + '/transcript')
        .then(r => r.json())
        .then(data => {{
          document.getElementById('modal-loading').style.display = 'none';
          if (data.error) {{
            document.getElementById('modal-error').textContent = data.error;
            document.getElementById('modal-error').style.display = 'block';
            return;
          }}
          const msgs = data.messages || [];
          if (!msgs.length) {{
            document.getElementById('modal-error').textContent = 'Sem mensagens na transcrição.';
            document.getElementById('modal-error').style.display = 'block';
            return;
          }}
          const container = document.getElementById('modal-messages');
          container.style.display = 'flex';
          msgs.forEach(m => {{
            const isAgent = m.role === 'MESSAGE_ROLE_AGENT';
            const start = m.timespan ? parseFloat(m.timespan.start) : null;
            const timeStr = start !== null ? formatSecs(start) : '';
            const wrap = document.createElement('div');
            wrap.style.cssText = 'display:flex;flex-direction:column;align-items:' + (isAgent ? 'flex-start' : 'flex-end');
            const label = document.createElement('div');
            label.style.cssText = 'font-size:10px;color:#94a3b8;margin-bottom:3px;padding:0 4px';
            label.textContent = (isAgent ? '🤖 Bruno' : '👤 Cliente') + (timeStr ? '  ' + timeStr : '');
            const bubble = document.createElement('div');
            bubble.style.cssText = 'max-width:85%;padding:10px 14px;border-radius:' +
              (isAgent ? '4px 16px 16px 16px' : '16px 4px 16px 16px') +
              ';background:' + (isAgent ? '#eff6ff' : '#f1f5f9') +
              ';color:' + (isAgent ? '#1e3a8a' : '#1e293b') +
              ';font-size:13px;line-height:1.5;border:1px solid ' +
              (isAgent ? '#bfdbfe' : '#e2e8f0');
            bubble.textContent = m.text.trim();
            wrap.appendChild(label);
            wrap.appendChild(bubble);
            container.appendChild(wrap);
          }});
        }})
        .catch(err => {{
          document.getElementById('modal-loading').style.display = 'none';
          document.getElementById('modal-error').textContent = 'Erro: ' + err;
          document.getElementById('modal-error').style.display = 'block';
        }});
    }}

    function closeModal() {{
      document.getElementById('modal-overlay').style.display = 'none';
      document.getElementById('modal').style.display = 'none';
    }}

    function formatSecs(s) {{
      const m = Math.floor(s / 60);
      const sec = Math.floor(s % 60);
      return m + ':' + String(sec).padStart(2, '0');
    }}

    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});
  </script>
</body>
</html>"""
        return Response(html, mimetype="text/html", status=200)

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

        # TwiML para o suporte: ouve o contexto e entra na conferência
        support_twiml = (
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

        # 1. Ligar ao suporte com contexto + conferência
        try:
            resp = twilio.session.post(
                f"{twilio.base_url}/Accounts/{twilio.account_sid}/Calls.json",
                data={
                    "To": TRANSFER_NUMBER,
                    "From": Config.TWILIO_FROM_NUMBER,
                    "Twiml": support_twiml,
                },
                auth=twilio.auth,
            )
            resp.raise_for_status()
            support_sid = resp.json().get("sid", "")
            logger.info(f"Warm transfer: suporte ligado | sid={support_sid} | conf={conference_name}")
        except Exception as e:
            logger.error(f"Warm transfer: erro ao ligar suporte: {e}")
            return jsonify({"error": "falha ao contactar suporte"}), 500

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
