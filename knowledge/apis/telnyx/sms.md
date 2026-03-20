# Telnyx — Envio de SMS

## Enviar SMS
```
POST /v2/messages
```

```python
import requests

def send_sms(
    to_number: str,
    from_number: str,
    text: str
) -> dict:
    """
    Envia SMS via Telnyx.

    Args:
        to_number: Número destino com DDI (+5511999999999)
        from_number: Seu número Telnyx (+5511000000000)
        text: Texto do SMS (máx 160 chars por segmento)

    Returns:
        dict com 'data.id' sendo o ID da mensagem
    """
    url = "https://api.telnyx.com/v2/messages"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": from_number,
        "to": to_number,
        "text": text,
        "messaging_profile_id": TELNYX_CONNECTION_ID  # opcional
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
```

## Exemplo de Resposta
```json
{
  "data": {
    "record_type": "message",
    "id": "40272ed9-7b52-4c75-a876-3eb05c485a0d",
    "type": "SMS",
    "direction": "outbound",
    "to": [{"phone_number": "+5511999999999", "status": "queued"}],
    "from": {"phone_number": "+5511000000000"},
    "text": "Olá! ...",
    "cost": {"amount": "0.00750", "currency": "USD"}
  }
}
```

## Status do SMS
- `queued` — na fila para envio
- `sending` — sendo enviado
- `sent` — enviado para operadora
- `delivered` — confirmado como entregue
- `failed` — falhou

## Verificar Status
```
GET /v2/messages/{id}
```

## SMS em Massa
Para enviar para muitos números, itere com pausa de 100ms entre cada:

```python
import time

def send_bulk_sms(numbers: list, message: str, from_number: str):
    results = []
    for number in numbers:
        try:
            result = send_sms(number, from_number, message)
            results.append({"number": number, "status": "ok", "id": result["data"]["id"]})
        except Exception as e:
            results.append({"number": number, "status": "error", "error": str(e)})
        time.sleep(0.1)  # 100ms entre envios
    return results
```
