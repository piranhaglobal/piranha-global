# Shopify — Webhooks

## Para que Serve
Receber notificações automáticas quando eventos ocorrem na loja (novo pedido, pagamento, etc.)

## Criar Webhook
```
POST /admin/api/2024-10/webhooks.json
```

```python
def create_webhook(topic: str, address: str) -> dict:
    """
    Cria webhook para receber eventos.

    Topics comuns:
    - orders/create — novo pedido
    - orders/paid — pedido pago
    - checkouts/update — checkout atualizado
    - customers/create — novo cliente
    """
    url = f"https://{STORE_URL}/admin/api/{VERSION}/webhooks.json"
    payload = {
        "webhook": {
            "topic": topic,
            "address": address,  # URL da sua VPS que receberá o webhook
            "format": "json"
        }
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    return response.json()
```

## Verificação de Webhook
Shopify envia o header `X-Shopify-Hmac-Sha256` — sempre verifique a assinatura por segurança.
