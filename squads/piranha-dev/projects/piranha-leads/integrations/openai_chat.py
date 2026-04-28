import os
from pathlib import Path

import requests


OPENAI_API_BASE = "https://api.openai.com/v1"


def _headers() -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definida")
    return {"Authorization": f"Bearer {api_key}"}


def chat_response(messages: list[dict], model: str | None = None) -> str:
    selected_model = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.2,
    }
    r = requests.post(
        f"{OPENAI_API_BASE}/chat/completions",
        headers={**_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=45,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()


def transcribe_audio(audio_path: str | Path, model: str | None = None) -> str:
    selected_model = model or os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
    language = os.getenv("OPENAI_TRANSCRIBE_LANGUAGE", "pt")
    path = Path(audio_path)
    with path.open("rb") as audio_file:
        r = requests.post(
            f"{OPENAI_API_BASE}/audio/transcriptions",
            headers=_headers(),
            data={"model": selected_model, "language": language},
            files={"file": (path.name, audio_file, "audio/webm")},
            timeout=90,
        )
    r.raise_for_status()
    return r.json().get("text", "").strip()
