# Evolution API — Gerenciar Instâncias

## Criar Instância
```
POST /instance/create
```

```python
def create_instance(instance_name: str) -> dict:
    url = f"{EVOLUTION_URL}/instance/create"
    payload = {
        "instanceName": instance_name,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    response = requests.post(url, headers={"apikey": API_KEY}, json=payload)
    return response.json()
```

## Verificar Status da Instância
```
GET /instance/connectionState/{instance}
```

```python
def check_connection(instance: str) -> str:
    """Retorna 'open', 'connecting', 'close'."""
    url = f"{EVOLUTION_URL}/instance/connectionState/{instance}"
    response = requests.get(url, headers={"apikey": API_KEY})
    data = response.json()
    return data.get("instance", {}).get("state", "unknown")
```

## Respostas de Status
- `open` — conectado ao WhatsApp
- `connecting` — conectando (aguardando QR Code)
- `close` — desconectado

## Reconectar / Buscar QR Code
```
GET /instance/connect/{instance}
```
