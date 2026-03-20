# Ultravox — Criar Chamadas

## Criar Chamada
```
POST /api/calls
```

```python
import requests

def create_ultravox_call(
    system_prompt: str,
    voice_id: str = "Mark",
    first_message: str = None,
    temperature: float = 0.8
) -> dict:
    """
    Cria uma chamada com agente de voz Ultravox.

    Args:
        system_prompt: Instruções do agente de voz
        voice_id: Voz a usar (Mark, Emily, etc.)
        first_message: Primeira fala do agente ao conectar
        temperature: Criatividade (0.0-1.0)

    Returns:
        dict com 'joinUrl' para conectar ao WebSocket da chamada
    """
    url = "https://api.ultravox.ai/api/calls"
    headers = {
        "X-API-Key": ULTRAVOX_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "systemPrompt": system_prompt,
        "model": "fixie-ai/ultravox",
        "voice": voice_id,
        "languageHint": "pt",
        "temperature": temperature,
        "firstSpeaker": "FIRST_SPEAKER_AGENT",
        # OBRIGATÓRIO para integração Twilio — sem isto não há áudio
        "medium": {
            "serverWebSocket": {
                "inputSampleRate": 8000,
                "outputSampleRate": 8000,
                "clientBufferSizeMs": 60,
            }
        },
    }

    if first_message:
        # Campo correto na API atual (firstSpeakerMessage foi removido)
        payload["firstSpeakerSettings"] = {"agent": {"text": first_message}}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()
    # Retorna: {"callId": "xxx", "joinUrl": "wss://...", "status": "created"}
```

## Exemplo de System Prompt para Carrinho Abandonado
```python
system_prompt = """
Você é um assistente de vendas da Piranha Global chamado Pedro.
Você está ligando para {nome_cliente} porque ele deixou produtos no carrinho.

Produtos abandonados:
{lista_produtos}

Valor total: R$ {valor_total}

Seu objetivo é:
1. Apresentar-se cordialmente
2. Perguntar se houve algum problema
3. Oferecer ajuda para finalizar a compra
4. Se necessário, oferecer cupom de 10% de desconto

Tom: Amigável, não insistente. Se a pessoa não quiser, agradeça e encerre.
Fale em português brasileiro natural.
"""
```

## Vozes Disponíveis (PT-BR)
- `Adriana` — feminino, neutro
- `Carlos` — masculino, neutro
- `Mark` — masculino (padrão global)

## Status de Chamada
```
GET /api/calls/{callId}
```

| Status | Significado |
|--------|-------------|
| `created` | Chamada criada, aguardando conexão |
| `active` | Chamada em andamento |
| `ended` | Chamada encerrada |
| `failed` | Falhou |

## Listar Chamadas
```
GET /api/calls?limit=50
```
