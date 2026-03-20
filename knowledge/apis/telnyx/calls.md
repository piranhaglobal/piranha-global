# Telnyx — Ligações Telefônicas

## Fazer Ligação Programática
```
POST /v2/calls
```

```python
def make_call(
    to_number: str,
    from_number: str,
    connection_id: str,
    webhook_url: str = None
) -> dict:
    """
    Inicia uma ligação telefônica via Telnyx.

    Para integrar com Ultravox, o webhook_url deve
    responder com instruções TeXML para conectar ao WebSocket Ultravox.
    """
    url = "https://api.telnyx.com/v2/calls"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "connection_id": connection_id,
        "to": to_number,
        "from": from_number,
        "webhook_url": webhook_url or f"{VPS_URL}/telnyx/webhook",
        "webhook_url_method": "POST"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
```

## Integração Telnyx + Ultravox

O fluxo para ligar com agente IA:

```
1. Criar chamada Ultravox → obter joinUrl (WebSocket)
2. Criar chamada Telnyx → o webhook recebe evento "call.answered"
3. Webhook responde com TeXML para conectar ao joinUrl do Ultravox
4. Ligação conecta: cliente fala com agente IA
```

### Exemplo de Webhook Handler (Flask)
```python
from flask import Flask, request, Response

app = Flask(__name__)

@app.route("/telnyx/webhook", methods=["POST"])
def telnyx_webhook():
    data = request.json
    event = data.get("data", {}).get("event_type", "")

    if event == "call.answered":
        # Conectar ao Ultravox
        call_id = create_ultravox_call(system_prompt="...")
        join_url = call_id["joinUrl"]

        # Responder com TeXML para conectar ao WebSocket
        texml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Connect>
                <Stream url="{join_url}" />
            </Connect>
        </Response>"""

        return Response(texml, mimetype="application/xml")

    return Response("OK", status=200)
```

## Status de Chamadas
- `parked` — na fila
- `bridging` — conectando
- `bridged` — em chamada ativa
- `hangup` — encerrada
