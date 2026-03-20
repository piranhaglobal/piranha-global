"""Cliente Ultravox — cria sessões de agente de voz."""

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# IDs das tools built-in Ultravox
_TOOL_HANG_UP = "56294126-5a7d-4948-b67d-3b7e13d55ea7"
_TOOL_COLD_TRANSFER = "2fff509d-273f-414e-91ff-aa933435a545"   # parameterOverrides: {target}
_TOOL_QUERY_CORPUS = "84a31bac-5c1b-41c3-9058-f81acb7ffaa7"   # parameterOverrides: {corpus_id}
_TOOL_LEAVE_VOICEMAIL = "8721c74d-af3f-4dfa-a736-3bc170ef917c"
# Destino de transferência (apoio humano)
_TRANSFER_NUMBER = "+351232468548"

# Corpus ID da knowledge base Piranha Supplies (Ultravox RAG)
_CORPUS_ID = "06436a6f-e604-4959-b15b-ca0b181c4a4c"


class UltravoxClient:
    BASE_URL = "https://api.ultravox.ai/api"
    MODEL = "ultravox-v0.7"

    def __init__(self) -> None:
        """Inicializa sessão HTTP com X-API-Key."""
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": Config.ULTRAVOX_API_KEY,
            "Content-Type": "application/json",
        })

    def create_call(
        self,
        system_prompt: str,
        language_hint: str,
        voice: str,
    ) -> dict:
        """
        Cria sessão de agente de voz na Ultravox API.
        Args:
            system_prompt: instruções completas do agente (variáveis já preenchidas)
            language_hint: "pt", "es", "fr" ou "en"
            voice: nome da voz Ultravox (usado apenas quando Cartesia não está configurada)
        Returns:
            dict com "callId" e "joinUrl"
        Raises:
            requests.HTTPError: se a API retornar erro
        """
        payload: dict = {
            "systemPrompt": system_prompt,
            "model": self.MODEL,
            "languageHint": language_hint,
            "temperature": 0.1,
            # SEGURANÇA: agente fala primeiro — obrigatório para chamadas outbound
            # uninterruptible: True → cliente não consegue interromper a abertura inicial
            # Após a abertura terminar, o barge-in normal volta a funcionar
            "firstSpeakerSettings": {"agent": {"uninterruptible": True}},
            # SEGURANÇA: duração máxima de 3 minutos por chamada
            "maxDuration": "180s",
            # Medium correto para Twilio Media Streams
            "medium": {"twilio": {}},
            # Tools built-in + custom
            "selectedTools": [
                {
                    "toolId": _TOOL_HANG_UP,
                },
                {
                    "toolId": _TOOL_COLD_TRANSFER,
                    "parameterOverrides": {"target": _TRANSFER_NUMBER},
                },
                {
                    "toolId": _TOOL_QUERY_CORPUS,
                    "parameterOverrides": {"corpus_id": _CORPUS_ID},
                },
                {
                    "toolId": _TOOL_LEAVE_VOICEMAIL,
                },
                {
                    "temporaryTool": {
                        "modelToolName": "logCallResult",
                        "description": (
                            "Regista o resultado final da chamada. "
                            "DEVE ser chamada antes de qualquer hangUp."
                        ),
                        "dynamicParameters": [
                            {
                                "name": "motivo_principal",
                                "location": "PARAMETER_LOCATION_BODY",
                                "schema": {
                                    "type": "string",
                                    "enum": [
                                        "esqueceu", "preço", "portes", "concorrente",
                                        "pesquisa", "problema_tecnico", "rejeição", "outro",
                                    ],
                                    "description": "Motivo principal da não-conclusão da compra.",
                                },
                                "required": True,
                            },
                            {
                                "name": "sub_motivo",
                                "location": "PARAMETER_LOCATION_BODY",
                                "schema": {
                                    "type": "string",
                                    "description": (
                                        "Detalhe adicional em texto livre. "
                                        "Ex: 'comprou na TattooShop24, entrega mais rápida'."
                                    ),
                                },
                                "required": False,
                            },
                            {
                                "name": "resultado",
                                "location": "PARAMETER_LOCATION_BODY",
                                "schema": {
                                    "type": "string",
                                    "enum": [
                                        "recuperado", "encerrado_sem_interesse",
                                        "encerrado_concorrente", "transferido",
                                        "sem_contacto", "apenas_pesquisa",
                                        "sem_decisao", "comprou_piranha",
                                    ],
                                    "description": "Resultado final da chamada.",
                                },
                                "required": True,
                            },
                        ],
                        "http": {
                            "baseUrlPattern": f"{Config.VPS_BASE_URL}/webhook/log-call-result",
                            "httpMethod": "POST",
                        },
                    },
                },
            ],
        }

        # Voz: nativa Ultravox clonada (ULTRAVOX_VOICE_ID) → Cartesia → fallback por idioma
        if Config.ULTRAVOX_VOICE_ID:
            payload["voice"] = Config.ULTRAVOX_VOICE_ID
            logger.info(f"A usar voz Ultravox clonada | voiceId={Config.ULTRAVOX_VOICE_ID[:8]}...")
        elif Config.CARTESIA_VOICE_ID and Config.CARTESIA_API_KEY:
            payload["externalVoice"] = {
                "cartesia": {
                    "voiceId": Config.CARTESIA_VOICE_ID,
                    "model": "sonic-3",
                    "speed": 0.9,
                }
            }
            logger.info(f"A usar voz Cartesia Sonic 3 | voiceId={Config.CARTESIA_VOICE_ID[:8]}...")
        else:
            payload["voice"] = voice
            logger.info(f"A usar voz Ultravox padrão | voice={voice}")

        response = self.session.post(f"{self.BASE_URL}/calls", json=payload)
        response.raise_for_status()
        data = response.json()

        logger.info(f"Sessão Ultravox criada | callId={data.get('callId')} | lang={language_hint} | model={self.MODEL}")
        return data  # {"callId": "...", "joinUrl": "wss://...", "status": "created"}

    def get_call_status(self, call_id: str) -> str:
        """
        Consulta o status de uma chamada Ultravox.
        Args:
            call_id: UUID da chamada
        Returns:
            "created" | "active" | "ended" | "failed"
        """
        response = self.session.get(f"{self.BASE_URL}/calls/{call_id}")
        response.raise_for_status()
        return response.json().get("status", "unknown")
