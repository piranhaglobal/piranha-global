"""Servidor Flask — recebe eventos Twilio e conecta cliente ao Ultravox via TwiML."""

import threading

from flask import Flask, Response, jsonify, request

from src.clients.twilio import TwilioClient
from src.clients.ultravox import TRANSFER_NUMBER
from src.config import Config
from src.handlers.call_handler import _sessions_lock, active_sessions, process_single
from src.utils import call_tracker
from src.utils.call_tracker import log_result_by_ultravox_id, get_record_by_ultravox_id
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
                # Verificar se o agente já marcou como voicemail (sem_contacto → no_answer_*)
                # Se sim, não sobrescrever com "completed"
                existing = call_tracker.get_record_by_provider_id(call_sid)
                if existing:
                    _, record = existing
                    if record.get("status") in {"no_answer_1", "no_answer_final"}:
                        logger.info(
                            f"Completed ignorado — status já definido como {record['status']} "
                            f"(voicemail detetado pelo agente) | sid={call_sid}"
                        )
                    else:
                        call_tracker.update_status(call_sid, "completed")
                else:
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
    <h1><img src="data:image/png;base64,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" style="height:32px;vertical-align:middle;margin-right:10px">Piranha Supplies Voice — Log de Chamadas</h1>
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

        # Voicemail detetado pelo agente — agenda retry igual a no-answer
        if resultado == "sem_contacto":
            result_record = None
            if call_sid:
                result_record = call_tracker.get_record_by_provider_id(call_sid)
            if not result_record and resolved_ultravox_id:
                result_record = get_record_by_ultravox_id(resolved_ultravox_id)
            if result_record:
                checkout_id, record = result_record
                if record.get("attempts", 1) < 2:
                    retry_date = next_business_day().isoformat()
                    call_tracker.mark_for_retry(checkout_id, retry_date)
                    logger.info(
                        f"Voicemail: retry agendado | checkout={checkout_id} | data={retry_date}"
                    )
                else:
                    call_tracker.mark_no_answer_final(checkout_id)
                    logger.info(
                        f"Voicemail: lead encerrado definitivamente | checkout={checkout_id}"
                    )

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
