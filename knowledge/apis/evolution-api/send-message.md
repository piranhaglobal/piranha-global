# Evolution API — Envio de Mensagens

## Enviar Mensagem de Texto
```
POST /message/sendText/{instance}
```

```python
def send_whatsapp_text(
    to_number: str,
    text: str,
    instance: str
) -> dict:
    """
    Envia mensagem de texto via WhatsApp.

    Args:
        to_number: Número com DDI (ex: "5511999999999")
        text: Texto da mensagem
        instance: Nome da instância Evolution

    Returns:
        dict com 'key.id' sendo o ID da mensagem enviada
    """
    url = f"{EVOLUTION_URL}/message/sendText/{instance}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": to_number,      # Formato: "5511999999999" (sem + ou -)
        "text": text,
        "delay": 1200             # Delay em ms (simula digitação humana)
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
```

## Enviar Imagem
```
POST /message/sendMedia/{instance}
```

```python
payload = {
    "number": "5511999999999",
    "mediatype": "image",
    "mimetype": "image/jpeg",
    "caption": "Veja este produto!",
    "media": "https://url-da-imagem.jpg"  # URL pública ou base64
}
```

## Enviar Documento
```python
payload = {
    "number": "5511999999999",
    "mediatype": "document",
    "mimetype": "application/pdf",
    "caption": "Seu pedido",
    "media": "https://url-do-pdf.pdf",
    "fileName": "pedido.pdf"
}
```

## Enviar Botões (Button Message)
```python
payload = {
    "number": "5511999999999",
    "title": "Seu carrinho está esperando!",
    "description": "Você tem itens no carrinho. Deseja finalizar a compra?",
    "footer": "Piranha Global",
    "buttons": [
        {"buttonId": "btn1", "buttonText": {"displayText": "Finalizar compra"}},
        {"buttonId": "btn2", "buttonText": {"displayText": "Não tenho interesse"}}
    ]
}
```

## Formato do Número
- `5511999999999` (DDI + DDD + número) — correto
- `+5511999999999` (com +) — incorreto
- `11999999999` (sem DDI) — incorreto
- `(11)99999-9999` (com formatação) — incorreto

## Exemplo de Resposta
```json
{
  "key": {
    "remoteJid": "5511999999999@s.whatsapp.net",
    "fromMe": true,
    "id": "3EB0B9C3D9F8A7B6"
  },
  "message": {
    "conversation": "Olá!"
  },
  "status": "PENDING"
}
```

## Boas Práticas Anti-Ban
1. Pause de 1-3 segundos entre mensagens
2. Não envie mais de 100 mensagens/hora por número
3. Varie levemente o texto (não mensagens idênticas em massa)
4. Prefira `delay: 1200` para simular comportamento humano
5. Nunca envie para números que pediram para parar
