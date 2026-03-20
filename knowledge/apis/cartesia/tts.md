# Cartesia — Text-to-Speech

## Gerar Áudio (Bytes)
```
POST /tts/bytes
```

```python
import requests

def text_to_speech(
    text: str,
    voice_id: str,
    output_format: str = "mp3"
) -> bytes:
    """
    Converte texto em áudio.

    Args:
        text: Texto a converter (máx ~5000 chars por requisição)
        voice_id: ID da voz Cartesia
        output_format: "mp3", "wav", "ogg"

    Returns:
        bytes do arquivo de áudio
    """
    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": "sonic-2",
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": voice_id
        },
        "output_format": {
            "container": output_format,
            "encoding": "mp3" if output_format == "mp3" else "pcm_f32le",
            "sample_rate": 44100
        },
        "language": "pt"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    return response.content  # bytes do áudio


def save_audio(text: str, voice_id: str, filename: str) -> str:
    """Gera áudio e salva em arquivo."""
    audio_bytes = text_to_speech(text, voice_id)

    with open(filename, "wb") as f:
        f.write(audio_bytes)

    return filename
```

## Streaming (para respostas em tempo real)
```
POST /tts/sse
```
Use Server-Sent Events para receber o áudio conforme é gerado.

## Clonar Voz
```
POST /voices/clone
```

```python
# Enviar arquivo de áudio de 30-60s para clonar a voz
files = {"clip": open("voz_referencia.mp3", "rb")}
data = {"name": "Voz Piranha", "language": "pt"}
response = requests.post(
    "https://api.cartesia.ai/voices/clone",
    headers={"X-API-Key": API_KEY},
    files=files,
    data=data
)
voice_id = response.json()["id"]
```

## Listar Vozes Disponíveis
```
GET /voices
```

## Vozes Recomendadas para PT-BR
- `694f9389-aac1-45b6-b726-9d9369183238` — Voz feminina natural
- `a0e99841-438c-4a64-b679-ae501e7d6091` — Voz masculina profissional

## Limites
- Máximo ~5000 caracteres por requisição no modelo sonic-2
- Rate limit: 100 req/min no plano padrão
