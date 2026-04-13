"""Cliente Ultravox — cria sessões de agente de voz."""

import requests

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# IDs das tools built-in Ultravox
_TOOL_HANG_UP = "56294126-5a7d-4948-b67d-3b7e13d55ea7"
_TOOL_QUERY_CORPUS = "84a31bac-5c1b-41c3-9058-f81acb7ffaa7"   # parameterOverrides: {corpus_id}
_TOOL_LEAVE_VOICEMAIL = "8721c74d-af3f-4dfa-a736-3bc170ef917c"
# Destino de transferência (apoio humano — warm transfer)
TRANSFER_NUMBER = "+351232468548"

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
            # Sem maxDuration — a chamada termina naturalmente via hangUp do agente.
            # Um limite fixo causaria desconexão abrupta a meio de uma fala.
            # Medium correto para Twilio Media Streams
            "medium": {"twilio": {}},
            # Ativa gravação para permitir playback no dashboard /admin/calls
            "recordingEnabled": True,
            # VAD — ajustado para chamadas outbound via Twilio (µ-law 8kHz)
            # Contexto: recuperação de checkout — clientes hesitam antes de responder;
            # chamadas móveis EU têm ruído de fundo e artefactos de codec frequentes.
            #
            # turnEndpointDelay:           0.512s (default 0.384s)
            #   → Dá espaço a pausas de decisão ("bem... não sei...") antes de responder.
            #   → Valor em múltiplo de 32ms conforme recomendação Ultravox.
            #
            # minimumTurnDuration:         0.2s (default 0s)
            #   → Ignora tosse, ruído de carro, speakerphone, artefactos de linha.
            #   → Evita que o Bruno responda a sons não-intencionais.
            #
            # minimumInterruptionDuration: 0.15s (default 0.09s)
            #   → Bruno completa frases críticas (ex: oferta de desconto) sem ser
            #     interrompido por respiros ou cliques de linha.
            #   → Interrupções genuínas ainda funcionam normalmente.
            #
            # frameActivationThreshold:    0.2 (default 0.1, escala 0.1–1.0)
            #   → Reduz falsos positivos do codec Twilio sem perder vozes baixas.
            #   → Ainda no extremo sensível da escala.
            "vadSettings": {
                "turnEndpointDelay": "0.512s",
                "minimumTurnDuration": "0.2s",
                "minimumInterruptionDuration": "0.15s",
                "frameActivationThreshold": 0.2,
            },
            # Tools built-in + custom
            "selectedTools": [
                {
                    "toolId": _TOOL_HANG_UP,
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
                        "modelToolName": "warmTransfer",
                        "description": (
                            "Transfere a chamada para um técnico humano com contexto da conversa. "
                            "USA ESTA TOOL em vez de hangUp quando o cliente aceitar ser transferido. "
                            "Fornece SEMPRE um resumo claro da conversa no parâmetro 'summary'. "
                            "Após chamar warmTransfer, usa logCallResult e depois hangUp."
                        ),
                        "dynamicParameters": [
                            {
                                "name": "summary",
                                "location": "PARAMETER_LOCATION_BODY",
                                "schema": {
                                    "type": "string",
                                    "description": (
                                        "Resumo da conversa e da dúvida ou motivo concreto "
                                        "do cliente para a transferência. "
                                        "Exemplo: 'Cliente Carlos, interessado na Kwadron Rotary Machine. "
                                        "Perguntou sobre voltagem — informação não disponível na descrição.'"
                                    ),
                                },
                                "required": True,
                            },
                        ],
                        "http": {
                            "baseUrlPattern": f"{Config.VPS_BASE_URL}/webhook/warm-transfer",
                            "httpMethod": "POST",
                        },
                    },
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

    def get_recording(self, call_id: str) -> dict:
        """
        Retorna a URL de gravação de uma chamada.
        Args:
            call_id: UUID da chamada Ultravox
        Returns:
            dict com "recordingUrl" (pode ser None se recording não estava ativo)
        Raises:
            requests.HTTPError: se a chamada não existir ou API falhar
        """
        response = self.session.get(f"{self.BASE_URL}/calls/{call_id}/recording")
        response.raise_for_status()
        return response.json()

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

    def get_transcript(self, call_id: str) -> list[dict]:
        """
        Busca a transcrição completa de uma chamada.
        Args:
            call_id: UUID da chamada Ultravox
        Returns:
            lista de mensagens ordenadas com role, text e timespan
        Raises:
            requests.HTTPError: se a chamada não existir ou API falhar
        """
        messages = []
        url = f"{self.BASE_URL}/calls/{call_id}/messages"
        while url:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            messages.extend(data.get("results", []))
            url = data.get("next")

        # Filtra apenas mensagens de voz e agente (remove eventos de sistema)
        relevant = [
            m for m in messages
            if m.get("role") in ("MESSAGE_ROLE_AGENT", "MESSAGE_ROLE_USER")
            and m.get("text", "").strip()
            and not m.get("text", "").startswith("(New Call)")
        ]
        return relevant
