# Mapeamento de Codigo: Post Purchase WhatsApp -- 4 Disparos

**Projecto:** `post-purchase-wpp`
**Agente:** @mapper (Max)
**Data:** 2026-03-10
**Versao:** 1.0
**Status:** Pronto para @dev
**Base:** Documentos `01-analyst-requirements.md`, `02-architect-blueprint.md`, `03-researcher-api-docs.md`

---

## Arvore de Arquivos

```
post-purchase-wpp/
├── src/
│   ├── __init__.py                              SEM ALTERACAO
│   ├── main.py                                  SEM ALTERACAO (mantido como legacy D4 runner)
│   ├── config.py                                MODIFICAR -- novas variaveis webhook, D3, suppression
│   ├── webhook_server.py                        NOVO -- entry point Flask para D1/D2
│   ├── message_worker.py                        NOVO -- daemon que consome fila e envia WhatsApp
│   ├── cron_d3.py                               NOVO -- cron diario para delay notifications
│   ├── cron_d4.py                               NOVO -- cron diario para reorder (refactored)
│   │
│   ├── clients/
│   │   ├── __init__.py                          SEM ALTERACAO
│   │   ├── shopify.py                           MODIFICAR -- 3 novos metodos + _extract_order expandido
│   │   └── evolution.py                         SEM ALTERACAO
│   │
│   ├── handlers/
│   │   ├── __init__.py                          SEM ALTERACAO
│   │   ├── message_handler.py                   MODIFICAR -- deprecated, wrapper legado
│   │   └── webhook_handler.py                   NOVO -- Flask app factory com rotas webhook
│   │
│   ├── prompts/
│   │   ├── __init__.py                          SEM ALTERACAO
│   │   ├── messages.py                          SEM ALTERACAO (mantido como legacy, deprecated)
│   │   ├── messages_d1.py                       NOVO -- templates D1 confirmacao (4 idiomas)
│   │   ├── messages_d2.py                       NOVO -- templates D2 tracking (4 idiomas)
│   │   ├── messages_d3.py                       NOVO -- templates D3 delay (4 idiomas, 2 versoes)
│   │   └── messages_d4.py                       NOVO -- templates D4 reorder (4 idiomas, 3 segmentos)
│   │
│   ├── utils/
│   │   ├── __init__.py                          SEM ALTERACAO
│   │   ├── logger.py                            SEM ALTERACAO
│   │   ├── sent_tracker.py                      MODIFICAR -- v2 multi-disparo + migracao + indices
│   │   ├── phone_normalizer.py                  SEM ALTERACAO
│   │   ├── language_detector.py                 SEM ALTERACAO
│   │   ├── schedule_checker.py                  SEM ALTERACAO
│   │   ├── queue_handler.py                     NOVO -- fila persistente JSON com prioridade + file lock
│   │   ├── suppression.py                       NOVO -- motor de 5 regras de supressao
│   │   └── hmac_validator.py                    NOVO -- validacao HMAC-SHA256 Shopify
│   │
│   └── scripts/
│       └── register_webhooks.py                 NOVO -- registo one-time de webhooks na Shopify
│
├── cache/
│   └── consumables.json                         SEM ALTERACAO
├── sent.json                                    MODIFICAR -- formato v2 (migracao automatica)
├── queue.json                                   NOVO -- fila persistente de mensagens
├── .env                                         MODIFICAR -- novas variaveis
└── requirements.txt                             MODIFICAR -- adicionar flask
```

---

## Estruturas de Dados Partilhadas

Estas TypedDicts definem os contratos de dados que circulam entre modulos. Devem ser definidas num ficheiro `src/types.py` (NOVO) e importadas por quem precisar.

### Arquivo: `src/types.py`

**Responsabilidade:** Definicoes de tipos partilhados (TypedDict, Literal) usados em todo o projecto
**Depende de:** nenhum
**Usado por:** todos os modulos

```python
from typing import Literal, TypedDict


# --- Tipo de disparo ---

DispatchType = Literal["D1", "D2", "D3", "D4"]


# --- Prioridades por disparo ---

DISPATCH_PRIORITY: dict[DispatchType, int] = {
    "D1": 1,  # Confirmacao -- maior urgencia
    "D2": 2,  # Tracking
    "D3": 3,  # Delay notification
    "D4": 4,  # Reorder -- menor urgencia
}


# --- Dados normalizados de um pedido ---

class LineItem(TypedDict):
    """Item de linha de um pedido Shopify."""
    product_id: int | None
    title: str
    quantity: int
    price: str


class OrderData(TypedDict, total=False):
    """Dados normalizados de um pedido, usados em todos os dispatches.

    Campos obrigatorios:
        id: ID do pedido Shopify (string)
        phone: telefone em formato E.164 (pode ser vazio)
        name: primeiro nome do cliente
        country_code: ISO 3166-1 alpha-2

    Campos opcionais (depende do dispatch):
        order_name: numero legivel (#XXXX)
        customer_id: ID do customer Shopify
        line_items: lista de itens do pedido
        total_price: valor total como string decimal
        currency: ISO 4217 (ex: EUR)
        fulfillment_status: null | "partial" | "fulfilled"
        created_at: data ISO 8601 de criacao do pedido
    """
    # Obrigatorios
    id: str
    phone: str
    name: str
    country_code: str
    # Opcionais
    order_name: str
    customer_id: str
    line_items: list[LineItem]
    total_price: str
    currency: str
    fulfillment_status: str | None
    created_at: str


# --- Item da fila de mensagens ---

class QueueItemData(TypedDict, total=False):
    """Dados especificos por tipo de dispatch dentro do queue item.

    D1: line_items, total_price, currency
    D2: tracking_url, tracking_number, tracking_company
    D3: order_name (para template)
    D4: segment, consumable_titles, line_items
    """
    line_items: list[LineItem]
    total_price: str
    currency: str
    tracking_url: str
    tracking_number: str
    tracking_company: str
    segment: str
    consumable_titles: list[str]
    order_name: str


class QueueItem(TypedDict):
    """Item na fila de mensagens (queue.json).

    Formato canonico usado por queue_handler, webhook_handler,
    cron_d3, cron_d4 e message_worker.

    Atributos:
        id: UUID v4 gerado no enqueue
        dispatch_type: "D1" | "D2" | "D3" | "D4"
        priority: 1 (D1) a 4 (D4) -- menor = mais urgente
        order_id: ID do pedido Shopify (string)
        order_name: numero legivel (#XXXX)
        customer_name: primeiro nome do cliente
        customer_id: ID do customer Shopify (string)
        phone: telefone em formato bruto (sera normalizado pelo worker)
        country_code: ISO 3166-1 alpha-2
        needs_order_fetch: True se dados do cliente precisam ser buscados na Shopify
        enqueued_at: ISO 8601 UTC timestamp de enfileiramento
        data: dados especificos do dispatch
    """
    id: str
    dispatch_type: DispatchType
    priority: int
    order_id: str
    order_name: str
    customer_name: str
    customer_id: str
    phone: str
    country_code: str
    needs_order_fetch: bool
    enqueued_at: str
    data: QueueItemData


# --- Registo no sent_tracker ---

class DispatchRecord(TypedDict, total=False):
    """Registo de um dispatch individual dentro do sent_tracker.

    Atributos:
        status: estado do dispatch
        timestamp: ISO 8601 do momento do registo
        msg_id: ID da mensagem Evolution API (se enviada)
        segment: segmento D4 (A/B/C) -- apenas para D4
        tracking_url: URL de tracking -- apenas para D2
    """
    status: str
    timestamp: str
    msg_id: str
    segment: str
    tracking_url: str


class SentRecord(TypedDict):
    """Registo de um pedido no sent_tracker v2 (sent.json).

    Atributos:
        phone: telefone normalizado
        name: primeiro nome do cliente
        country_code: ISO 3166-1 alpha-2
        language: codigo de idioma (pt/es/fr/en)
        dispatches: mapa dispatch_type -> DispatchRecord
    """
    phone: str
    name: str
    country_code: str
    language: str
    dispatches: dict[str, DispatchRecord]
```

---

## Arquivos NOVOS

---

### Arquivo: `src/utils/hmac_validator.py`

**Responsabilidade:** Validar assinatura HMAC-SHA256 dos webhooks enviados pela Shopify
**Depende de:** `src/config.py`
**Usado por:** `src/handlers/webhook_handler.py`

```python
import base64
import hashlib
import hmac

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def validate(raw_body: bytes, hmac_header: str) -> bool:
    """
    Valida que o webhook foi realmente enviado pela Shopify.

    Compara o HMAC-SHA256 computado localmente com o header
    X-Shopify-Hmac-Sha256 enviado pela Shopify.

    IMPORTANTE: No Flask, chamar request.get_data() ANTES de
    request.get_json() porque get_json() consome o stream.

    Args:
        raw_body: corpo do request HTTP em bytes (request.get_data())
        hmac_header: valor do header X-Shopify-Hmac-Sha256 (base64)

    Returns:
        True se a assinatura e valida, False caso contrario

    Raises:
        Nao levanta excepcoes -- retorna False em caso de erro
    """
```

#### Constantes

```python
# Nenhuma constante publica -- usa Config.SHOPIFY_WEBHOOK_SECRET
```

---

### Arquivo: `src/utils/queue_handler.py`

**Responsabilidade:** Fila persistente em ficheiro JSON com prioridade FIFO e file locking (fcntl.flock) para concorrencia entre webhook server, worker e cron
**Depende de:** `src/utils/logger.py`, `src/types.py`
**Usado por:** `src/handlers/webhook_handler.py`, `src/message_worker.py`, `src/cron_d3.py`, `src/cron_d4.py`

```python
import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.types import QueueItem
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

QUEUE_FILE: Path = Path(__file__).parent.parent.parent / "queue.json"

LOCK_TIMEOUT_SECONDS: int = 10  # timeout para aquisicao do file lock


class MessageQueue:
    """
    Fila de mensagens persistente em JSON com prioridade e file locking.

    A fila e ordenada por (priority ASC, enqueued_at ASC) -- menor
    prioridade numerica = mais urgente, FIFO dentro da mesma prioridade.

    Concorrencia: usa fcntl.flock(LOCK_EX) para garantir atomicidade
    entre webhook server (enqueue), worker (peek/dequeue) e cron (enqueue).

    Formato do queue.json:
    {
      "items": [ QueueItem, QueueItem, ... ]
    }
    """

    def __init__(self, queue_file: Path = QUEUE_FILE) -> None:
        """
        Inicializa a fila apontando para o ficheiro de persistencia.

        Args:
            queue_file: caminho do ficheiro JSON da fila (default: queue.json na raiz)
        """

    def enqueue(self, item: dict) -> str:
        """
        Adiciona item a fila, ordenado por prioridade.

        Gera automaticamente o campo 'id' (UUID v4) e 'enqueued_at' (UTC ISO).
        Ordena a lista por (priority ASC, enqueued_at ASC) apos insercao.
        Usa file lock exclusivo durante a operacao.

        Args:
            item: dicionario com todos os campos de QueueItem EXCEPTO 'id' e 'enqueued_at'
                  (estes sao gerados automaticamente)

        Returns:
            string UUID do item enfileirado

        Raises:
            TimeoutError: se nao conseguir adquirir file lock em LOCK_TIMEOUT_SECONDS
            OSError: erro de I/O no ficheiro
        """

    def peek(self) -> QueueItem | None:
        """
        Retorna o proximo item da fila SEM remover.

        O proximo item e o primeiro da lista ordenada (menor prioridade + mais antigo).
        Usa file lock partilhado (LOCK_SH) para leitura.

        Returns:
            QueueItem se houver items, None se fila vazia

        Raises:
            TimeoutError: se nao conseguir adquirir file lock
        """

    def dequeue(self) -> QueueItem | None:
        """
        Remove e retorna o proximo item da fila.

        Usa file lock exclusivo (LOCK_EX).

        Returns:
            QueueItem removido, None se fila vazia

        Raises:
            TimeoutError: se nao conseguir adquirir file lock
        """

    def size(self) -> int:
        """
        Retorna o numero de items na fila.

        Returns:
            inteiro >= 0
        """

    def _load(self) -> dict:
        """
        Le queue.json com file lock.

        Se o ficheiro nao existir, cria-o com {"items": []}.
        Se estiver corrompido, log warning e retorna {"items": []}.

        Returns:
            dict com chave "items" contendo lista de QueueItem
        """

    def _save(self, data: dict) -> None:
        """
        Escreve queue.json com file lock exclusivo.

        IMPORTANTE: Esta funcao deve ser chamada DENTRO de um bloco
        que ja detm o lock exclusivo (nao adquire lock proprio).

        Args:
            data: dict com chave "items"
        """

    def _acquire_lock(self, file_handle, lock_type: int) -> None:
        """
        Adquire file lock com timeout usando signal.alarm.

        Args:
            file_handle: file object aberto
            lock_type: fcntl.LOCK_EX (exclusivo) ou fcntl.LOCK_SH (partilhado)

        Raises:
            TimeoutError: se o lock nao for adquirido em LOCK_TIMEOUT_SECONDS
        """
```

---

### Arquivo: `src/utils/suppression.py`

**Responsabilidade:** Motor de 5 regras de supressao que decide se um envio deve ser bloqueado
**Depende de:** `src/utils/sent_tracker.py`, `src/clients/shopify.py`, `src/config.py`, `src/utils/logger.py`
**Usado por:** `src/message_worker.py`

```python
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import Config
from src.types import DispatchType
from src.utils import sent_tracker
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def check_all(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None" = None,
    order_data: dict | None = None,
) -> tuple[bool, str]:
    """
    Executa todas as regras de supressao aplicaveis ao dispatch.

    As regras sao avaliadas em ordem. Na primeira regra violada,
    retorna imediatamente (short-circuit).

    Ordem de avaliacao:
      1. SUP01 -- cooldown 4h por telefone (todos os dispatches)
      2. SUP02 -- max 3 mensagens em 7 dias por telefone (todos)
      3. SUP05 -- cooldown review request 24h (todos, graceful skip se nao configurado)
      4. SUP04 -- skip se fulfilled (apenas D3)
      5. SUP03 -- skip se recompra (apenas D4)

    Args:
        phone: telefone normalizado do destinatario
        order_id: ID do pedido Shopify
        dispatch_type: "D1" | "D2" | "D3" | "D4"
        shopify: instancia ShopifyClient para verificacoes em tempo real
                 (SUP03, SUP04). None = skip dessas regras.
        order_data: dados adicionais do pedido (customer_id, created_at)
                    necessarios para SUP03. None = skip SUP03.

    Returns:
        tuple (suppressed: bool, rule_code: str)
        Se suppressed=False: ("", False) -- pode enviar
        Se suppressed=True: (True, "SUP01") -- suprimido, com codigo da regra

    Raises:
        Nao levanta excepcoes -- erros em regras individuais sao logados
        e a regra e ignorada (fail-open para nao bloquear envios)
    """


def _check_sup01_cooldown_4h(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None",
    order_data: dict | None,
) -> tuple[bool, str]:
    """
    SUP01: Max 1 WhatsApp por telefone a cada 4 horas.

    Consulta sent_tracker.get_last_send_timestamp(phone) e verifica
    se (now - last_send) >= 4 horas.

    Args:
        phone: telefone normalizado
        order_id: (nao usado nesta regra)
        dispatch_type: (nao usado nesta regra)
        shopify: (nao usado nesta regra)
        order_data: (nao usado nesta regra)

    Returns:
        (True, "SUP01") se cooldown violado, (False, "") caso contrario
    """


def _check_sup02_max_3_7days(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None",
    order_data: dict | None,
) -> tuple[bool, str]:
    """
    SUP02: Max 3 mensagens automaticas por telefone em 7 dias.

    Consulta sent_tracker.count_sends_last_7_days(phone) e verifica
    se count >= 3.

    Args:
        phone: telefone normalizado
        order_id: (nao usado)
        dispatch_type: (nao usado)
        shopify: (nao usado)
        order_data: (nao usado)

    Returns:
        (True, "SUP02") se limite atingido, (False, "") caso contrario
    """


def _check_sup03_reorder(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None",
    order_data: dict | None,
) -> tuple[bool, str]:
    """
    SUP03: Verificar recompra antes de D4.

    Apenas aplicavel a D4. Para outros dispatches, retorna (False, "").
    Se shopify ou order_data nao estiverem disponiveis, skip (fail-open).

    Chama shopify.check_reorder(customer_id, created_at).
    Se o customer fez nova compra desde o pedido original, suprimir.

    Args:
        phone: (nao usado)
        order_id: (nao usado directamente)
        dispatch_type: deve ser "D4" para activar
        shopify: instancia ShopifyClient (obrigatorio para funcionar)
        order_data: deve conter "customer_id" e "created_at"

    Returns:
        (True, "SUP03") se recompra detectada, (False, "") caso contrario
    """


def _check_sup04_fulfilled(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None",
    order_data: dict | None,
) -> tuple[bool, str]:
    """
    SUP04: D3 skip se pedido ja foi fulfilled.

    Apenas aplicavel a D3. Re-verifica fulfillment_status em tempo real
    via shopify.get_order(order_id). Safety net -- o cron_d3 ja faz
    esta verificacao, mas entre o enqueue e o envio pode ter mudado.

    Args:
        phone: (nao usado)
        order_id: ID do pedido para re-verificar
        dispatch_type: deve ser "D3" para activar
        shopify: instancia ShopifyClient (obrigatorio para funcionar)
        order_data: (nao usado)

    Returns:
        (True, "SUP04") se fulfilled, (False, "") caso contrario
    """


def _check_sup05_review_request(
    phone: str,
    order_id: str,
    dispatch_type: DispatchType,
    shopify: "ShopifyClient | None",
    order_data: dict | None,
) -> tuple[bool, str]:
    """
    SUP05: Cooldown de 24h se Review Request activo para o telefone.

    Implementacao provisoria baseada em ficheiro JSON.
    Formato do ficheiro: { "telefone_normalizado": "ISO_timestamp_activacao" }

    Se Config.REVIEW_REQUEST_FILE estiver vazio ou ficheiro nao existir,
    esta regra e silenciosamente ignorada (fail-open).

    Args:
        phone: telefone normalizado para lookup
        order_id: (nao usado)
        dispatch_type: (nao usado)
        shopify: (nao usado)
        order_data: (nao usado)

    Returns:
        (True, "SUP05") se review request activo ha menos de 24h,
        (False, "") caso contrario ou se nao configurado
    """
```

---

### Arquivo: `src/handlers/webhook_handler.py`

**Responsabilidade:** Flask app factory com rotas para webhooks Shopify (orders/paid, fulfillments/create) e healthcheck
**Depende de:** `flask`, `src/utils/hmac_validator.py`, `src/utils/queue_handler.py`, `src/utils/sent_tracker.py`, `src/clients/evolution.py`, `src/config.py`, `src/types.py`
**Usado por:** `src/webhook_server.py`

```python
import json
import time
from datetime import datetime, timezone

from flask import Flask, Response, request

from src.clients.evolution import EvolutionClient
from src.config import Config
from src.types import DISPATCH_PRIORITY
from src.utils import hmac_validator, sent_tracker
from src.utils.logger import setup_logger
from src.utils.queue_handler import MessageQueue

logger = setup_logger(__name__)

# Timestamp de inicio do servidor para calculo de uptime
_START_TIME: float  # inicializado em create_app()


def create_app() -> Flask:
    """
    Cria e configura a aplicacao Flask com 3 rotas:
      - POST /webhooks/orders/paid
      - POST /webhooks/fulfillments/create
      - GET  /health

    Returns:
        instancia Flask configurada, pronta para app.run()

    Raises:
        Nao levanta excepcoes -- erros em rotas sao tratados internamente
    """


def _handle_order_paid() -> tuple[str, int]:
    """
    Rota POST /webhooks/orders/paid -- recebe webhook Shopify orders/paid.

    Fluxo:
      1. Ler raw body (bytes) ANTES de parse JSON (necessario para HMAC)
      2. Validar HMAC via hmac_validator.validate()
         Se invalido: return ("Unauthorized", 401)
      3. Parse JSON do body
      4. Extrair campos do pedido para QueueItem:
         - order_id: str(payload["id"])
         - order_name: payload["name"]
         - customer_name: payload.get("customer", {}).get("first_name") or "cliente"
         - phone: payload.get("phone") or payload.get("customer", {}).get("phone") or ""
         - country_code: payload.get("shipping_address", {}).get("country_code") or "PT"
         - customer_id: str(payload.get("customer", {}).get("id", ""))
         - line_items: [{product_id, title, quantity, price} for item in payload["line_items"]]
         - total_price: payload["total_price"]
         - currency: payload["currency"]
      5. Montar dict de QueueItem com dispatch_type="D1", priority=1
      6. MessageQueue().enqueue(item)
      7. Log info com order_id
      8. return ("OK", 200)

    Returns:
        tuple (body, status_code) -- sempre responde em < 100ms

    Raises:
        Nao propaga excepcoes -- erros sao logados e retorna 500
    """


def _handle_fulfillment_create() -> tuple[str, int]:
    """
    Rota POST /webhooks/fulfillments/create -- recebe webhook Shopify fulfillments/create.

    Fluxo:
      1. Ler raw body + validar HMAC (idem D1)
         Se invalido: return ("Unauthorized", 401)
      2. Parse JSON
      3. Verificar se tracking_url esta presente e nao vazia
         Se ausente: log info "fulfillment sem tracking, ignorado", return ("OK", 200)
      4. Extrair campos do fulfillment:
         - order_id: str(payload["order_id"])
         - tracking_number: payload.get("tracking_number", "")
         - tracking_url: payload["tracking_url"]
         - tracking_company: payload.get("tracking_company", "")
      5. Tentar obter dados do cliente do sent_tracker:
         order_data = sent_tracker.get_order_data(str(order_id))
         Se encontrou: usar phone, customer_name, country_code do tracker
         Se nao: marcar needs_order_fetch=True (worker buscara via Shopify API)
      6. Montar dict de QueueItem com dispatch_type="D2", priority=2
      7. MessageQueue().enqueue(item)
      8. return ("OK", 200)

    Returns:
        tuple (body, status_code)
    """


def _health_check() -> tuple[Response, int]:
    """
    Rota GET /health -- retorna estado do sistema.

    Formato de resposta JSON:
    {
      "status": "ok",
      "whatsapp_instance": "open" | "close" | "connecting" | "error",
      "queue_size": int,
      "last_send": "ISO_timestamp" | null,
      "uptime_seconds": int
    }

    Returns:
        tuple (Response JSON, 200)
    """
```

---

### Arquivo: `src/webhook_server.py`

**Responsabilidade:** Entry point que inicializa e executa o servidor Flask de webhooks
**Depende de:** `src/handlers/webhook_handler.py`, `src/config.py`
**Usado por:** systemd (executado como `python -m src.webhook_server`)

```python
from src.config import Config
from src.handlers.webhook_handler import create_app
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main() -> None:
    """
    Entry point do webhook server.

    Fluxo:
      1. Config.validate(mode="webhook") -- valida variaveis incluindo SHOPIFY_WEBHOOK_SECRET
      2. app = create_app()
      3. Log info com porta
      4. app.run(host="0.0.0.0", port=Config.SERVER_PORT, debug=False)

    Raises:
        ValueError: se variaveis obrigatorias estiverem ausentes
        SystemExit: se a porta estiver em uso
    """


# if __name__ == "__main__":
#     main()
```

---

### Arquivo: `src/message_worker.py`

**Responsabilidade:** Daemon continuo que consome a fila de mensagens e envia WhatsApp via Evolution API. Este e o UNICO processo que chama evolution.send_text().
**Depende de:** `src/utils/queue_handler.py`, `src/utils/suppression.py`, `src/utils/sent_tracker.py`, `src/utils/phone_normalizer.py`, `src/utils/language_detector.py`, `src/utils/schedule_checker.py`, `src/clients/evolution.py`, `src/clients/shopify.py`, `src/prompts/messages_d1.py`, `src/prompts/messages_d2.py`, `src/prompts/messages_d3.py`, `src/prompts/messages_d4.py`, `src/config.py`, `src/types.py`
**Usado por:** systemd (executado como `python -m src.message_worker`)

```python
import signal
import sys
import time

from src.clients.evolution import EvolutionClient
from src.clients.shopify import ShopifyClient
from src.config import Config
from src.prompts import messages_d1, messages_d2, messages_d3, messages_d4
from src.types import DispatchType, QueueItem
from src.utils import sent_tracker, suppression
from src.utils.language_detector import get_language
from src.utils.logger import setup_logger
from src.utils.phone_normalizer import normalize
from src.utils.queue_handler import MessageQueue
from src.utils.schedule_checker import is_business_hours, seconds_until_business_hours

logger = setup_logger(__name__)

# Intervalo de polling quando a fila esta vazia (segundos)
POLL_INTERVAL: int = 30

# Intervalo de retry quando instancia Evolution esta offline (segundos)
EVOLUTION_RETRY_INTERVAL: int = 60

# Flag para shutdown gracioso
_shutdown_requested: bool = False


def main() -> None:
    """
    Loop principal do worker daemon.

    Fluxo do loop infinito:
      1. item = queue.peek()
         Se fila vazia: sleep(POLL_INTERVAL), continue
      2. Verificar horario comercial
         Se fora: sleep(seconds_until_business_hours()), continue
      3. Verificar instancia Evolution online
         Se offline: sleep(EVOLUTION_RETRY_INTERVAL), continue
      4. Se item.needs_order_fetch == True:
         Chamar shopify.get_order(item.order_id)
         Preencher phone, customer_name, country_code no item
      5. Normalizar telefone via phone_normalizer.normalize()
         Se invalido: dequeue, mark "skipped_no_phone", continue
      6. Verificar supressao via suppression.check_all()
         Se suprimido: dequeue, mark "skipped_suppressed", continue
      7. Gerar mensagem via handler correspondente ao dispatch_type
      8. Enviar via evolution.send_text(phone, message)
         Se erro: dequeue, mark "error", continue
      9. dequeue -- remover da fila
      10. mark dispatch no sent_tracker com status="sent" e msg_id
      11. sleep(Config.SEND_DELAY_SECONDS) -- 300s anti-ban

    Tratamento de sinais:
      SIGTERM / SIGINT -> _shutdown_requested = True
      O loop termina apos completar o envio actual (nao interrompe mid-send)

    Raises:
        ValueError: se Config.validate() falhar
    """


def _build_message(item: QueueItem) -> str:
    """
    Gera a mensagem de texto para o dispatch_type do item.

    Routing:
      "D1" -> messages_d1.build(language, name, order_name, items, total, currency)
      "D2" -> messages_d2.build(language, name, tracking_url, tracking_company)
      "D3" -> messages_d3.build(language, name, order_name, edu_url)
      "D4" -> _build_d4_message(item, language)

    Args:
        item: QueueItem completo (ja com dados do pedido preenchidos)

    Returns:
        string pronta para envio via Evolution API

    Raises:
        ValueError: se dispatch_type nao for reconhecido
        ValueError: se idioma ou segmento nao for suportado (propagado dos templates)
    """


def _build_d4_message(item: QueueItem, language: str) -> str:
    """
    Gera mensagem D4 com routing por segmento.

    Routing:
      segment "A" -> messages_d4.build_segment_a(language, name, consumable_titles)
      segment "B" -> messages_d4.build_segment_b(language, name)
      segment "C" -> messages_d4.build_segment_c(language, name)

    Args:
        item: QueueItem com data.segment e data.consumable_titles
        language: codigo de idioma (pt/es/fr/en)

    Returns:
        string pronta para envio

    Raises:
        ValueError: se segmento nao for A, B ou C
    """


def _setup_signal_handlers() -> None:
    """
    Regista handlers para SIGTERM e SIGINT que setam _shutdown_requested=True.

    O worker termina graciosamente apos completar o envio actual.
    """
```

---

### Arquivo: `src/cron_d3.py`

**Responsabilidade:** Cron job diario que busca pedidos pagos 3-5 dias atras sem fulfillment e enfileira D3. NAO envia mensagens.
**Depende de:** `src/clients/shopify.py`, `src/utils/queue_handler.py`, `src/utils/sent_tracker.py`, `src/utils/schedule_checker.py`, `src/clients/evolution.py`, `src/config.py`, `src/types.py`
**Usado por:** crontab (executado como `python -m src.cron_d3`)

```python
from src.clients.evolution import EvolutionClient
from src.clients.shopify import ShopifyClient
from src.config import Config
from src.types import DISPATCH_PRIORITY
from src.utils import sent_tracker
from src.utils.logger import setup_logger
from src.utils.queue_handler import MessageQueue
from src.utils.schedule_checker import is_business_hours

logger = setup_logger(__name__)


def main() -> None:
    """
    Entry point do cron D3.

    Fluxo:
      1. Config.validate()
      2. Verificar horario comercial -- se fora, encerrar
      3. Verificar instancia Evolution -- se offline, encerrar com warning
      4. shopify.get_orders_unfulfilled_window(days_min=3, days_max=5)
      5. Para cada pedido:
         a. Se sent_tracker.is_dispatched(order_id, "D3"): skip, log
         b. Re-verificar: shopify.get_order(order_id)
            Se fulfillment_status == "fulfilled": mark "skipped_fulfilled", skip
         c. Extrair dados (phone, name, country_code, order_name)
         d. queue.enqueue({dispatch_type: "D3", priority: 3, data: {order_name: ...}})
      6. Log resumo: "D3: X enfileirados, Y skipped"

    Returns:
        None (script termina apos enfileirar)

    Raises:
        ValueError: se Config.validate() falhar
    """


# if __name__ == "__main__":
#     main()
```

---

### Arquivo: `src/cron_d4.py`

**Responsabilidade:** Cron job diario que busca pedidos do dia 25, classifica em 3 segmentos (A/B/C) e enfileira D4. Substitui a logica do main.py actual.
**Depende de:** `src/clients/shopify.py`, `src/utils/queue_handler.py`, `src/utils/sent_tracker.py`, `src/utils/schedule_checker.py`, `src/clients/evolution.py`, `src/config.py`, `src/types.py`
**Usado por:** crontab (executado como `python -m src.cron_d4`)

```python
from src.clients.evolution import EvolutionClient
from src.clients.shopify import ShopifyClient
from src.config import Config
from src.types import DISPATCH_PRIORITY
from src.utils import sent_tracker
from src.utils.logger import setup_logger
from src.utils.queue_handler import MessageQueue
from src.utils.schedule_checker import is_business_hours

logger = setup_logger(__name__)


def main() -> None:
    """
    Entry point do cron D4.

    Fluxo:
      1. Config.validate()
      2. Verificar horario comercial -- se fora, encerrar
      3. Verificar instancia Evolution -- se offline, encerrar com warning
      4. shopify.get_orders_day_25() (metodo ja existente)
      5. consumable_ids = shopify.get_consumable_ids() (metodo ja existente)
      6. Para cada pedido:
         a. Se sent_tracker.is_dispatched(order_id, "D4"): skip
         b. customer_id = order["customer_id"]
         c. Se shopify.check_reorder(customer_id, order["created_at"]):
            mark "skipped_reordered", skip
         d. segment = classify_d4(order, consumable_ids, shopify)
         e. consumable_titles = extrair titulos consumiveis (se segment == "A")
         f. queue.enqueue({dispatch_type: "D4", priority: 4,
            data: {segment, consumable_titles, line_items}})
      7. Log resumo: "D4: X enfileirados, Y skipped"

    Returns:
        None

    Raises:
        ValueError: se Config.validate() falhar
    """


def classify_d4(
    order: dict,
    consumable_ids: set[int],
    shopify: ShopifyClient,
) -> str:
    """
    Classifica pedido em segmento D4 (3-way).

    Logica:
      1. Se algum line_item.product_id esta em consumable_ids -> "A" (B2C consumiveis)
      2. Senao, buscar customer tags via shopify.get_customer(customer_id)
         Se tags contem "wholesale" ou "b2b" (case-insensitive) -> "C" (B2B)
      3. Senao -> "B" (B2C nao consumiveis)

    Args:
        order: dict normalizado com line_items e customer_id
        consumable_ids: set de product_ids da coleccao consumiveis
        shopify: instancia ShopifyClient para buscar customer tags

    Returns:
        "A" | "B" | "C"

    Raises:
        Nao levanta excepcoes -- se get_customer falhar, assume "B"
    """


# if __name__ == "__main__":
#     main()
```

---

### Arquivo: `src/prompts/messages_d1.py`

**Responsabilidade:** Templates de mensagem D1 (confirmacao de pedido) em 4 idiomas com 3 variantes de abertura anti-ban
**Depende de:** `random` (stdlib)
**Usado por:** `src/message_worker.py`

```python
import random

from src.types import LineItem

# Variantes de abertura para anti-ban (seleccao aleatoria por envio)
GREETING_VARIANTS: dict[str, list[str]] = {
    "pt": ["Ola {name}", "Bom dia {name}", "{name}, tudo bem"],
    "es": ["Hola {name}", "Buenos dias {name}", "{name}, que tal"],
    "fr": ["Bonjour {name}", "{name}, bonjour", "Cher {name}"],
    "en": ["Hi {name}", "Hello {name}", "{name}, good day"],
}

ASSINATURA: str = "\n\n-- Piranha Supplies"

SUPPORTED_LANGUAGES: set[str] = {"pt", "es", "fr", "en"}


def build(
    language: str,
    customer_name: str,
    order_name: str,
    line_items: list[LineItem],
    total_price: str,
    currency: str,
) -> str:
    """
    Gera mensagem de confirmacao de pedido (D1).

    Conteudo:
      - Saudacao personalizada (variante aleatoria)
      - Confirmacao do pedido com numero (#XXXX)
      - Lista de itens (nome x quantidade)
      - Valor total + moeda
      - Informacao de que recebera tracking quando enviado
      - Assinatura "-- Piranha Supplies"

    Regras de copy:
      - ZERO emojis
      - Tom profissional, tecnico, confiavel
      - Personalizado com primeiro nome

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome do cliente
        order_name: numero do pedido (ex: "#1042")
        line_items: lista de LineItem com title e quantity
        total_price: valor total como string (ex: "89.50")
        currency: codigo ISO 4217 (ex: "EUR")

    Returns:
        string completa pronta para envio via Evolution API

    Raises:
        ValueError: se language nao for suportado
    """
```

---

### Arquivo: `src/prompts/messages_d2.py`

**Responsabilidade:** Templates de mensagem D2 (envio + tracking) em 4 idiomas com 3 variantes de abertura
**Depende de:** `random` (stdlib)
**Usado por:** `src/message_worker.py`

```python
import random

GREETING_VARIANTS: dict[str, list[str]]  # identico a d1
ASSINATURA: str = "\n\n-- Piranha Supplies"
SUPPORTED_LANGUAGES: set[str] = {"pt", "es", "fr", "en"}


def build(
    language: str,
    customer_name: str,
    tracking_url: str,
    tracking_company: str,
) -> str:
    """
    Gera mensagem de envio + tracking (D2).

    Conteudo:
      - Saudacao personalizada (variante aleatoria)
      - Confirmacao de que o pedido foi enviado
      - Tracking URL clicavel
      - Transportadora (se disponivel)
      - Prazo estimado de entrega
      - Assinatura "-- Piranha Supplies"

    Regras de copy: ZERO emojis, tom profissional.

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome do cliente
        tracking_url: URL completa de rastreio
        tracking_company: nome da transportadora (pode ser vazio)

    Returns:
        string completa pronta para envio

    Raises:
        ValueError: se language nao for suportado
    """
```

---

### Arquivo: `src/prompts/messages_d3.py`

**Responsabilidade:** Templates de mensagem D3 (notificacao de atraso) em 4 idiomas, 2 versoes (com link educativo / fallback) e 3 variantes de abertura
**Depende de:** `random` (stdlib)
**Usado por:** `src/message_worker.py`

```python
import random

GREETING_VARIANTS: dict[str, list[str]]  # identico a d1
ASSINATURA: str = "\n\n-- Piranha Supplies"
SUPPORTED_LANGUAGES: set[str] = {"pt", "es", "fr", "en"}


def build(
    language: str,
    customer_name: str,
    order_name: str,
    edu_url: str = "",
) -> str:
    """
    Gera mensagem de notificacao de atraso (D3).

    Se edu_url nao vazio: versao completa com link educativo.
    Se edu_url vazio: versao fallback mais curta, sem link.

    Conteudo (versao completa):
      - Saudacao personalizada
      - Reconhecimento de que o pedido ainda esta a ser preparado
      - Garantia de que esta a ser tratado
      - Link para conteudo educativo
      - Assinatura

    Conteudo (versao fallback):
      - Saudacao personalizada
      - Reconhecimento de que o pedido esta a ser preparado
      - Garantia de que sera enviado brevemente
      - Assinatura

    Regras de copy: ZERO emojis, tom empatico mas profissional.

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome do cliente
        order_name: numero do pedido (ex: "#1042")
        edu_url: URL de conteudo educativo (vazio = usar fallback)

    Returns:
        string completa pronta para envio

    Raises:
        ValueError: se language nao for suportado
    """
```

---

### Arquivo: `src/prompts/messages_d4.py`

**Responsabilidade:** Templates de mensagem D4 (reorder/cross-sell) em 4 idiomas, 3 segmentos (A/B/C) e 3 variantes de abertura. Substitui logica do messages.py actual.
**Depende de:** `random` (stdlib)
**Usado por:** `src/message_worker.py`

```python
import random

GREETING_VARIANTS: dict[str, list[str]]  # identico a d1
ASSINATURA: str = "\n\n-- Piranha Supplies"
SUPPORTED_LANGUAGES: set[str] = {"pt", "es", "fr", "en"}


def build_segment_a(
    language: str,
    customer_name: str,
    consumable_titles: list[str],
) -> str:
    """
    Gera mensagem D4 para Segmento A (B2C consumiveis).

    Foco: reposicao de stock dos consumiveis comprados.

    Conteudo:
      - Saudacao personalizada
      - Referencia a 25 dias desde a ultima encomenda
      - Lista de consumiveis comprados
      - Incentivo a reposicao
      - Link piranhasupplies.com
      - Assinatura

    Diferencas do messages.py actual:
      - ZERO emojis (actual usa shark e rock hand)
      - Assinatura "-- Piranha Supplies" (actual nao tem)
      - Variantes de abertura

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome do cliente
        consumable_titles: lista de nomes dos consumiveis comprados

    Returns:
        string completa pronta para envio

    Raises:
        ValueError: se language nao for suportado
    """


def build_segment_b(
    language: str,
    customer_name: str,
) -> str:
    """
    Gera mensagem D4 para Segmento B (B2C nao consumiveis).

    Foco: cross-sell de consumiveis (cliente comprou equipamento
    mas nao comprou consumiveis).

    Conteudo:
      - Saudacao personalizada
      - Referencia ao equipamento adquirido
      - Sugestao de consumiveis complementares
      - Link para coleccao consumiveis
      - Assinatura

    NOTA: No codigo actual, B e agrupado com A como "A_B".
    Na nova implementacao, B e separado com copy proprio.

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome

    Returns:
        string completa pronta para envio

    Raises:
        ValueError: se language nao for suportado
    """


def build_segment_c(
    language: str,
    customer_name: str,
) -> str:
    """
    Gera mensagem D4 para Segmento C (B2B/Wholesale).

    Foco: reposicao com tom B2B profissional.

    Conteudo:
      - Saudacao formal
      - Referencia a parceria B2B
      - Incentivo a reposicao de stock para o estudio/loja
      - Link piranhasupplies.com
      - Assinatura

    Args:
        language: "pt" | "es" | "fr" | "en"
        customer_name: primeiro nome

    Returns:
        string completa pronta para envio

    Raises:
        ValueError: se language nao for suportado
    """


def _format_product_list(titles: list[str]) -> str:
    """
    Formata lista de produtos como texto para a mensagem.

    Args:
        titles: lista de nomes de produtos

    Returns:
        string com um produto por linha precedido de "  - "
        Se lista vazia: retorna "  - (produtos nao especificados)"
    """
```

---

### Arquivo: `scripts/register_webhooks.py`

**Responsabilidade:** Script one-time para registar webhooks orders/paid e fulfillments/create na Shopify. Verifica duplicados antes de criar.
**Depende de:** `src/clients/shopify.py`, `src/config.py`
**Usado por:** operador humano (executado manualmente uma vez)

```python
from src.clients.shopify import ShopifyClient
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Webhooks a registar
WEBHOOKS_TO_REGISTER: list[dict[str, str]] = [
    {"topic": "orders/paid", "path": "/webhooks/orders/paid"},
    {"topic": "fulfillments/create", "path": "/webhooks/fulfillments/create"},
]


def main() -> None:
    """
    Regista webhooks na Shopify se ainda nao existirem.

    Fluxo:
      1. Config.validate(mode="webhook") -- precisa de WEBHOOK_BASE_URL
      2. Instanciar ShopifyClient
      3. GET /webhooks.json para listar webhooks existentes
      4. Para cada webhook em WEBHOOKS_TO_REGISTER:
         a. Se topic ja existe: log info "ja registado", skip
         b. POST /webhooks.json com topic + address (WEBHOOK_BASE_URL + path) + format="json"
         c. Log info com webhook_id retornado
      5. Log resumo

    Returns:
        None

    Raises:
        ValueError: se variaveis obrigatorias ausentes
        requests.HTTPError: erro na API Shopify
    """


def _list_existing_webhooks(shopify: ShopifyClient) -> dict[str, int]:
    """
    Lista webhooks existentes na Shopify.

    Args:
        shopify: instancia ShopifyClient

    Returns:
        dict mapeando topic -> webhook_id (ex: {"orders/paid": 901234567})

    Raises:
        requests.HTTPError: erro na API Shopify
    """


def _register_webhook(shopify: ShopifyClient, topic: str, address: str) -> int | None:
    """
    Regista um webhook na Shopify.

    Args:
        shopify: instancia ShopifyClient
        topic: topico do webhook (ex: "orders/paid")
        address: URL HTTPS completa de destino

    Returns:
        webhook_id (int) se registado com sucesso, None se falhou

    Raises:
        requests.HTTPError: erro na API Shopify
    """


# if __name__ == "__main__":
#     main()
```

---

## Arquivos MODIFICADOS

---

### Arquivo: `src/config.py` # MODIFICADO

**Responsabilidade:** Carrega e valida variaveis de ambiente do projecto
**Depende de:** `os`, `dotenv`
**Usado por:** todos os modulos

#### Novas variaveis de classe a adicionar:

```python
class Config:
    # --- EXISTENTES (sem alteracao) ---
    SHOPIFY_STORE_URL: str
    SHOPIFY_ACCESS_TOKEN: str
    SHOPIFY_API_VERSION: str
    SHOPIFY_CONSUMABLES_HANDLE: str
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE: str
    SEND_DELAY_SECONDS: int

    # --- NOVAS ---
    SHOPIFY_WEBHOOK_SECRET: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    # Secret para validacao HMAC dos webhooks Shopify

    WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "")
    # URL publica HTTPS do servidor webhook (ex: https://webhook.dominio.com)

    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    # Porta do servidor Flask (atras de nginx reverse proxy)

    EDUCATIONAL_CONTENT_URL: str = os.getenv("EDUCATIONAL_CONTENT_URL", "")
    # URL de conteudo educativo para D3 (vazio = usar template fallback)

    REVIEW_REQUEST_FILE: str = os.getenv("REVIEW_REQUEST_FILE", "")
    # Path para ficheiro review_requests.json (vazio = skip SUP05)
```

#### Metodo validate MODIFICADO:

```python
    # Listas de variaveis obrigatorias por modo
    _REQUIRED_BASE: list[str] = [
        "SHOPIFY_STORE_URL",
        "SHOPIFY_ACCESS_TOKEN",
        "EVOLUTION_API_URL",
        "EVOLUTION_API_KEY",
        "EVOLUTION_INSTANCE",
    ]

    _REQUIRED_WEBHOOK: list[str] = _REQUIRED_BASE + [
        "SHOPIFY_WEBHOOK_SECRET",
    ]

    @classmethod
    def validate(cls, mode: str = "base") -> None:  # MODIFICADO -- novo parametro mode
        """
        Valida que todas as variaveis obrigatorias estao presentes.

        Dois modos:
          - "base": valida variaveis minimas (para cron D3/D4 e worker)
          - "webhook": valida variaveis base + SHOPIFY_WEBHOOK_SECRET (para webhook server)

        Args:
            mode: "base" (default) ou "webhook"

        Raises:
            ValueError: com lista das variaveis ausentes
        """
```

---

### Arquivo: `src/clients/shopify.py` # MODIFICADO

**Responsabilidade:** Cliente Shopify Admin REST API -- pedidos, customers, fulfillments, consumiveis, webhooks
**Depende de:** `requests`, `src/config.py`, `src/utils/logger.py`
**Usado por:** `src/cron_d3.py`, `src/cron_d4.py`, `src/message_worker.py`, `src/utils/suppression.py`, `scripts/register_webhooks.py`

#### Novos metodos a adicionar a classe ShopifyClient:

```python
    def get_order(self, order_id: str) -> dict:  # NOVO
        """
        Busca um pedido especifico pelo ID via GET /orders/{order_id}.json.

        Usado para:
          - Re-verificacao de fulfillment_status em tempo real (D3, SUP04)
          - Fetch de dados do cliente quando D2 webhook nao traz info (needs_order_fetch)

        Args:
            order_id: ID do pedido Shopify (string)

        Returns:
            dict normalizado com campos:
              id: str
              name: str (ex: "#1042")
              fulfillment_status: str | None ("fulfilled" | "partial" | None)
              customer_id: str
              customer_name: str
              phone: str (formato E.164, pode ser vazio)
              country_code: str (ISO 3166-1 alpha-2)
              line_items: list[LineItem]
              total_price: str
              currency: str
              created_at: str (ISO 8601)

        Raises:
            requests.HTTPError: pedido nao encontrado (404) ou erro de rede
        """

    def get_orders_unfulfilled_window(
        self,
        days_min: int = 3,
        days_max: int = 5,
    ) -> list[dict]:  # NOVO
        """
        Busca pedidos pagos criados entre days_max e days_min dias atras
        que ainda NAO foram totalmente enviados (unfulfilled ou partial).

        Faz DUAS requests a Shopify API:
          1. fulfillment_status=unfulfilled
          2. fulfillment_status=partial
        Combina os resultados e remove duplicados por order_id.

        NOTA: A API Shopify nao suporta multiplos valores no parametro
        fulfillment_status, por isso sao necessarias 2 requests separadas.

        Args:
            days_min: limite inferior da janela em dias (default 3)
            days_max: limite superior da janela em dias (default 5)

        Returns:
            lista de dicts normalizados via _extract_order_extended()
            Inclui campos extra: customer_id, order_name, total_price,
            currency, fulfillment_status, created_at

        Raises:
            requests.HTTPError: falha na API Shopify
        """

    def get_customer(self, customer_id: str) -> dict:  # NOVO
        """
        Busca dados do customer via GET /customers/{customer_id}.json.

        Usado para verificar tags B2B (D4 segmento C).

        Args:
            customer_id: ID do customer Shopify (string)

        Returns:
            dict com:
              id: str
              first_name: str
              tags: str (tags separadas por virgula, ex: "wholesale, premium")
              phone: str

        Raises:
            requests.HTTPError: customer nao encontrado (404) ou erro de rede
        """

    def check_reorder(self, customer_id: str, since_date: str) -> bool:  # NOVO
        """
        Verifica se o customer fez nova compra desde since_date.

        Chama GET /orders.json com customer_id e created_at_min=since_date.
        Se retornar mais de 1 pedido (o primeiro pode ser o proprio original),
        o customer fez recompra.

        Args:
            customer_id: ID do customer Shopify
            since_date: data ISO 8601 do pedido original

        Returns:
            True se existe pedido mais recente com financial_status=paid

        Raises:
            requests.HTTPError: erro na API Shopify
            Nota: se a API falhar, retorna False (fail-open para nao bloquear D4)
        """
```

#### Metodo _extract_order MODIFICADO:

```python
    def _extract_order(self, order: dict) -> dict:  # MODIFICADO
        """
        Normaliza campos relevantes de um pedido bruto da Shopify.

        MODIFICACAO: Adiciona campos customer_id, order_name, total_price,
        currency, fulfillment_status e created_at ao dict retornado.
        Tambem adiciona quantity e price a cada line_item.

        Args:
            order: dict bruto da API Shopify

        Returns:
            dict com:
              id: str
              phone: str
              name: str (primeiro nome, fallback "cliente")
              country_code: str (ISO alpha-2, fallback "PT")
              customer_id: str  # NOVO
              order_name: str   # NOVO (ex: "#1042")
              line_items: list[{product_id, title, quantity, price}]  # MODIFICADO -- quantity e price adicionados
              total_price: str  # NOVO
              currency: str     # NOVO
              fulfillment_status: str | None  # NOVO
              created_at: str   # NOVO
        """
```

---

### Arquivo: `src/utils/sent_tracker.py` # MODIFICADO

**Responsabilidade:** Persiste e consulta o estado de cada envio por pedido e por dispatch (formato v2 multi-disparo)
**Depende de:** `json`, `datetime`, `pathlib`, `fcntl`, `src/utils/logger.py`
**Usado por:** `src/message_worker.py`, `src/handlers/webhook_handler.py`, `src/utils/suppression.py`, `src/cron_d3.py`, `src/cron_d4.py`

#### Funcoes NOVAS:

```python
import fcntl

from src.types import DispatchRecord, DispatchType, SentRecord

# Formato v2 do sent.json:
# {
#   "order_id": {
#     "phone": "351912345678",
#     "name": "Joao",
#     "country_code": "PT",
#     "language": "pt",
#     "dispatches": {
#       "D1": {"status": "sent", "timestamp": "...", "msg_id": "3EB0..."},
#       "D4": {"status": "sent", "timestamp": "...", "segment": "A"}
#     }
#   }
# }

# Status possiveis por dispatch:
VALID_STATUSES: set[str] = {
    "sent", "pending", "queued",
    "skipped_fulfilled", "skipped_reordered", "skipped_no_phone",
    "skipped_suppressed", "skipped_cooldown", "error",
}


def is_dispatched(order_id: str, dispatch_type: DispatchType) -> bool:  # NOVO
    """
    Verifica se um disparo especifico ja foi enviado com sucesso para o pedido.

    Args:
        order_id: ID do pedido Shopify (string)
        dispatch_type: "D1" | "D2" | "D3" | "D4"

    Returns:
        True se dispatches[dispatch_type]["status"] == "sent"
    """


def mark_dispatch(
    order_id: str,
    dispatch_type: DispatchType,
    status: str,
    msg_id: str = "",
    phone: str = "",
    name: str = "",
    country_code: str = "",
    language: str = "",
    **extra: str,
) -> None:  # NOVO
    """
    Regista um disparo no sent_tracker v2.

    Se o pedido nao existir, cria a entrada completa.
    Se o pedido ja existir, apenas adiciona/actualiza o dispatch.
    Se o dispatch ja tiver status "sent", NAO sobrescreve com status inferior.

    Usa file lock exclusivo (fcntl.flock) para concorrencia.

    Args:
        order_id: ID do pedido Shopify
        dispatch_type: "D1" | "D2" | "D3" | "D4"
        status: um dos VALID_STATUSES
        msg_id: ID da mensagem Evolution API (opcional, apenas para "sent")
        phone: telefone normalizado (obrigatorio se pedido nao existir)
        name: primeiro nome (obrigatorio se pedido nao existir)
        country_code: ISO alpha-2 (obrigatorio se pedido nao existir)
        language: codigo idioma (obrigatorio se pedido nao existir)
        **extra: campos extras para o DispatchRecord (ex: segment="A", tracking_url="...")

    Raises:
        Nao levanta excepcoes -- erros sao logados
    """


def get_order_data(order_id: str) -> dict | None:  # NOVO
    """
    Retorna dados base do pedido se existir no tracker.

    Usado pelo webhook_handler para obter phone/name/country_code
    de um pedido que ja teve D1 processado (evita call extra a Shopify).

    Args:
        order_id: ID do pedido Shopify

    Returns:
        dict com {phone, name, country_code, language} ou None se nao existir
    """


def get_last_send_timestamp(phone: str) -> "datetime | None":  # NOVO
    """
    Retorna timestamp do ultimo envio bem-sucedido para este telefone.

    Percorre todos os pedidos, todos os dispatches, filtra status=="sent",
    e retorna o timestamp mais recente associado a este phone.

    Complexidade: O(n) onde n = total de dispatches. Aceitavel para < 50k registos.

    Args:
        phone: telefone normalizado (apenas digitos com DDI)

    Returns:
        datetime UTC do ultimo envio, ou None se nunca enviado
    """


def count_sends_last_7_days(phone: str) -> int:  # NOVO
    """
    Conta envios bem-sucedidos nos ultimos 7 dias para este telefone.

    Percorre todos os pedidos, todos os dispatches, filtra:
      - status == "sent"
      - phone == phone do pedido
      - timestamp > (now - 7 dias)

    Args:
        phone: telefone normalizado

    Returns:
        inteiro >= 0
    """


def get_last_global_send_timestamp() -> str | None:  # NOVO
    """
    Retorna timestamp ISO do ultimo envio global (qualquer pedido/dispatch).

    Usado pelo health check.

    Returns:
        string ISO 8601 ou None se nenhum envio registado
    """


def _migrate_v1_to_v2(data: dict) -> dict:  # NOVO
    """
    Migra registos do formato v1 (actual) para v2 (multi-disparo).

    Deteccao: um registo v1 NAO tem chave "dispatches".
    Um registo v2 TEM chave "dispatches".

    Regras de migracao:
      1. Todo registo v1 e tratado como D4 (unico disparo que existia)
      2. "segment" move para dentro de dispatches.D4
      3. "status" move para dentro de dispatches.D4
      4. "timestamp" move para dentro de dispatches.D4
      5. "country_code" e inferido ou default "PT"
      6. "language" e preservado

    Args:
        data: dict do sent.json (pode ter mix de v1 e v2)

    Returns:
        dict completamente em formato v2
    """
```

#### Funcoes EXISTENTES mantidas como wrappers (deprecated):

```python
def is_sent(order_id: str) -> bool:  # MODIFICADO -- wrapper legado
    """
    [DEPRECATED] Verifica se QUALQUER disparo foi enviado para o pedido.

    Mantido para backward compatibility com main.py.
    Internamente verifica todos os dispatches e retorna True se algum
    tem status "sent".

    Args:
        order_id: ID do pedido Shopify

    Returns:
        True se qualquer dispatch tem status "sent"
    """


def mark(  # MODIFICADO -- wrapper legado
    order_id: str,
    phone: str,
    name: str,
    segment: str,
    language: str,
    status: str,
) -> None:
    """
    [DEPRECATED] Regista envio no formato legado.

    Mantido para backward compatibility com message_handler.py.
    Internamente chama mark_dispatch com dispatch_type="D4".

    Args:
        order_id: ID do pedido
        phone: telefone normalizado
        name: primeiro nome
        segment: "A_B" | "C" | "-"
        language: "pt" | "es" | "fr" | "en" | "-"
        status: "sent" | "no_phone_skip" | "already_sent_skip" | "error"
    """
```

#### Funcoes internas MODIFICADAS:

```python
def _load() -> dict:  # MODIFICADO
    """
    Le sent.json com file lock partilhado (LOCK_SH).

    Na primeira leitura, detecta registos v1 e executa migracao automatica.
    Apos migracao, salva o ficheiro em formato v2.

    Returns:
        dict em formato v2 (todos os registos com "dispatches")
    """


def _save(data: dict) -> None:  # MODIFICADO
    """
    Escreve sent.json com file lock exclusivo (LOCK_EX).

    Args:
        data: dict em formato v2
    """
```

---

### Arquivo: `src/handlers/message_handler.py` # MODIFICADO

**Responsabilidade:** [DEPRECATED] Mantido para backward compatibility com main.py. A logica de dispatch D4 e agora feita pelo cron_d4.py + message_worker.py.
**Depende de:** (mesmas dependencias actuais)
**Usado por:** `src/main.py` (legacy)

#### Alteracoes:

```python
# Adicionar no topo do ficheiro:
# import warnings
# warnings.warn(
#     "message_handler.py esta deprecated. Usar cron_d4.py + message_worker.py.",
#     DeprecationWarning, stacklevel=2
# )

# NENHUMA funcao e removida -- process_orders, process_single, classify
# continuam a funcionar exactamente como antes para manter main.py operacional
# durante a transicao.
```

---

## Fluxo de Dados

### D1 -- Confirmacao de Pedido

```
Shopify (webhook orders/paid)
    │
    ▼
webhook_handler._handle_order_paid()
    │ 1. request.get_data() → raw_body (bytes)
    │ 2. hmac_validator.validate(raw_body, hmac_header)
    │ 3. json.loads(raw_body) → payload
    │ 4. Extrair campos → QueueItem{dispatch_type="D1", priority=1}
    │ 5. MessageQueue().enqueue(item)
    │ 6. return ("OK", 200)
    ▼
queue.json (persistido em disco com file lock)
    │
    ▼
message_worker.main() [loop continuo]
    │ 1. queue.peek() → item
    │ 2. schedule_checker.is_business_hours() → True/False
    │ 3. evolution.check_instance() → True/False
    │ 4. phone_normalizer.normalize(item.phone, item.country_code) → phone
    │ 5. suppression.check_all(phone, order_id, "D1") → (suppressed, rule)
    │ 6. messages_d1.build(language, name, order_name, items, total, currency) → text
    │ 7. evolution.send_text(phone, text) → {key: {id: msg_id}}
    │ 8. queue.dequeue()
    │ 9. sent_tracker.mark_dispatch(order_id, "D1", "sent", msg_id, ...)
    │ 10. time.sleep(300)
    ▼
sent.json (registo D1 com msg_id)
```

### D2 -- Envio + Tracking

```
Shopify (webhook fulfillments/create)
    │
    ▼
webhook_handler._handle_fulfillment_create()
    │ 1. Validar HMAC
    │ 2. Verificar tracking_url presente → se nao: return 200 + log skip
    │ 3. sent_tracker.get_order_data(order_id) → dados cliente (ou None)
    │ 4. Se None: needs_order_fetch=True
    │ 5. QueueItem{dispatch_type="D2", priority=2, data={tracking_url, ...}}
    │ 6. MessageQueue().enqueue(item)
    ▼
queue.json
    │
    ▼
message_worker.main()
    │ 1. queue.peek() → item
    │ 2. Se item.needs_order_fetch:
    │    shopify.get_order(order_id) → preencher phone, name, country_code
    │ 3. Normalizar, verificar supressao
    │ 4. messages_d2.build(language, name, tracking_url, tracking_company) → text
    │ 5. evolution.send_text(phone, text) → msg_id
    │ 6. sent_tracker.mark_dispatch(order_id, "D2", "sent", msg_id, tracking_url=...)
    ▼
sent.json (registo D2)
```

### D3 -- Notificacao de Atraso

```
crontab (diario 08h05 seg-sab)
    │
    ▼
cron_d3.main()
    │ 1. Config.validate()
    │ 2. is_business_hours() → True/False
    │ 3. evolution.check_instance() → True/False
    │ 4. shopify.get_orders_unfulfilled_window(3, 5) → orders[]
    │    └── GET /orders.json?fulfillment_status=unfulfilled (request 1)
    │    └── GET /orders.json?fulfillment_status=partial    (request 2)
    │ 5. Para cada order:
    │    a. sent_tracker.is_dispatched(order_id, "D3") → skip se True
    │    b. shopify.get_order(order_id) → re-verificar fulfillment_status
    │       Se "fulfilled": sent_tracker.mark_dispatch(..., "skipped_fulfilled")
    │    c. MessageQueue().enqueue({dispatch_type="D3", priority=3})
    ▼
queue.json
    │
    ▼
message_worker.main()
    │ 1-3. Verificacoes habituais
    │ 4. suppression.check_all(phone, order_id, "D3", shopify=shopify)
    │    └── _check_sup04_fulfilled → shopify.get_order(order_id) [safety net]
    │ 5. messages_d3.build(language, name, order_name, edu_url) → text
    │ 6. evolution.send_text(phone, text)
    │ 7. sent_tracker.mark_dispatch(order_id, "D3", "sent", msg_id)
    ▼
sent.json (registo D3)
```

### D4 -- Reorder / Cross-sell

```
crontab (diario 08h05 seg-sab, apos D3)
    │
    ▼
cron_d4.main()
    │ 1. Config.validate()
    │ 2. is_business_hours(), evolution.check_instance()
    │ 3. shopify.get_orders_day_25() → orders[]
    │    └── GET /orders.json?created_at_min={-26d}&created_at_max={-24d}
    │ 4. shopify.get_consumable_ids() → consumable_ids (set)
    │    └── GET /custom_collections.json + GET /collects.json (com cache)
    │ 5. Para cada order:
    │    a. sent_tracker.is_dispatched(order_id, "D4") → skip se True
    │    b. shopify.check_reorder(customer_id, created_at) → skip se True
    │       └── GET /orders.json?customer_id={id}&created_at_min={date}&limit=2
    │    c. classify_d4(order, consumable_ids, shopify) → segment (A/B/C)
    │       └── Se nao A: shopify.get_customer(customer_id) → verificar tags B2B
    │           └── GET /customers/{id}.json
    │    d. MessageQueue().enqueue({dispatch_type="D4", priority=4, data={segment, ...}})
    ▼
queue.json
    │
    ▼
message_worker.main()
    │ 1-3. Verificacoes habituais
    │ 4. suppression.check_all(phone, order_id, "D4", shopify, order_data)
    │    └── _check_sup03_reorder [safety net]
    │ 5. _build_d4_message(item, language):
    │    segment "A" → messages_d4.build_segment_a(language, name, consumable_titles)
    │    segment "B" → messages_d4.build_segment_b(language, name)
    │    segment "C" → messages_d4.build_segment_c(language, name)
    │ 6. evolution.send_text(phone, text)
    │ 7. sent_tracker.mark_dispatch(order_id, "D4", "sent", msg_id, segment=...)
    ▼
sent.json (registo D4 com segmento)
```

---

## Mapa de Endpoints → Funcoes

### Endpoints que o sistema CHAMA (APIs externas)

| Endpoint | Metodo | Funcao que chama | Arquivo | Dispatch |
|----------|--------|-----------------|---------|----------|
| `GET /admin/api/2024-10/orders.json` (day 25) | GET | `ShopifyClient.get_orders_day_25()` | `src/clients/shopify.py` | D4 |
| `GET /admin/api/2024-10/orders.json` (unfulfilled 3-5d) | GET | `ShopifyClient.get_orders_unfulfilled_window()` | `src/clients/shopify.py` | D3 |
| `GET /admin/api/2024-10/orders.json` (reorder check) | GET | `ShopifyClient.check_reorder()` | `src/clients/shopify.py` | D4 (SUP03) |
| `GET /admin/api/2024-10/orders/{order_id}.json` | GET | `ShopifyClient.get_order()` | `src/clients/shopify.py` | D2, D3 (SUP04) |
| `GET /admin/api/2024-10/customers/{customer_id}.json` | GET | `ShopifyClient.get_customer()` | `src/clients/shopify.py` | D4 |
| `GET /admin/api/2024-10/custom_collections.json` | GET | `ShopifyClient._fetch_collection_id()` | `src/clients/shopify.py` | D4 |
| `GET /admin/api/2024-10/collects.json` | GET | `ShopifyClient._fetch_product_ids()` | `src/clients/shopify.py` | D4 |
| `POST /admin/api/2024-10/webhooks.json` | POST | `_register_webhook()` | `scripts/register_webhooks.py` | Setup |
| `GET /admin/api/2024-10/webhooks.json` | GET | `_list_existing_webhooks()` | `scripts/register_webhooks.py` | Setup |
| `POST /message/sendText/{instance}` | POST | `EvolutionClient.send_text()` | `src/clients/evolution.py` | D1, D2, D3, D4 |
| `GET /instance/connectionState/{instance}` | GET | `EvolutionClient.check_instance()` | `src/clients/evolution.py` | Todos |

### Endpoints que o sistema RECEBE (webhook server)

| Endpoint | Metodo | Funcao handler | Arquivo | Dispatch |
|----------|--------|---------------|---------|----------|
| `POST /webhooks/orders/paid` | POST | `_handle_order_paid()` | `src/handlers/webhook_handler.py` | D1 |
| `POST /webhooks/fulfillments/create` | POST | `_handle_fulfillment_create()` | `src/handlers/webhook_handler.py` | D2 |
| `GET /health` | GET | `_health_check()` | `src/handlers/webhook_handler.py` | Monitoramento |

---

## Dependencias Externas (requirements.txt)

```
requests==2.31.0        # HTTP client para Shopify Admin API e Evolution API
python-dotenv==1.0.0    # Carregamento de variaveis de ambiente do .env
pytz==2024.1            # Timezone Europe/Lisbon para horario comercial
flask==3.0.3            # NOVO -- servidor HTTP para receber webhooks Shopify
```

**NOTA sobre dependencias stdlib utilizadas (nao precisam de pip install):**
- `hmac`, `hashlib`, `base64` -- validacao HMAC-SHA256
- `fcntl` -- file locking para concorrencia (Linux/macOS)
- `json` -- persistencia JSON
- `uuid` -- geracao de IDs para items da fila
- `signal` -- shutdown gracioso e timeout de file lock
- `random` -- seleccao de variantes de abertura anti-ban
- `time`, `datetime` -- delays, timestamps, calculos temporais
- `pathlib` -- caminhos de ficheiros
- `typing` -- TypedDict, Literal

---

## Processos na VPS

| Processo | Tipo | Gestao | Entry Point | Descricao |
|----------|------|--------|-------------|-----------|
| Webhook Server | Continuo | systemd | `python -m src.webhook_server` | Recebe webhooks Shopify, valida HMAC, enfileira D1/D2 |
| Message Worker | Continuo | systemd | `python -m src.message_worker` | Consome fila, verifica supressao, envia WhatsApp, regista |
| Cron D3 | Diario 08h05 | crontab | `python -m src.cron_d3` | Busca pedidos 3-5d sem envio, enfileira D3 |
| Cron D4 | Diario 08h05 | crontab | `python -m src.cron_d4` | Busca pedidos dia 25, classifica, enfileira D4 |

**Crontab sugerido:**
```bash
# D3+D4 seg-sab 08h05 Europe/Lisbon
5 8 * * 1-6 cd /home/ubuntu/projetos/post-purchase-wpp && /home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.cron_d3 >> /var/log/piranha-wpp-cron-d3.log 2>&1
6 8 * * 1-6 cd /home/ubuntu/projetos/post-purchase-wpp && /home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.cron_d4 >> /var/log/piranha-wpp-cron-d4.log 2>&1
```

---

## Notas para o @dev

1. **Ordem de implementacao sugerida:** `src/types.py` -> `hmac_validator` -> `queue_handler` -> `suppression` -> `sent_tracker` v2 -> `config.py` -> `shopify.py` novos metodos -> `webhook_handler` -> `webhook_server` -> templates D1-D4 -> `message_worker` -> `cron_d3` -> `cron_d4` -> `register_webhooks.py` -> `message_handler.py` deprecated

2. **File locking:** Todos os acessos a `queue.json` e `sent.json` DEVEM usar `fcntl.flock`. O webhook server e o worker correm em paralelo e acedem aos mesmos ficheiros.

3. **Migracao sent.json:** A funcao `_migrate_v1_to_v2()` deve ser chamada automaticamente no primeiro `_load()` que detectar formato v1. NAO requer intervencao manual.

4. **Backward compatibility:** O `main.py`, `message_handler.py` e `messages.py` actuais NAO sao alterados na sua funcionalidade. Continuam operacionais durante a transicao. Apenas `sent_tracker.py` muda internamente mas mantm a API legada.

5. **Anti-ban critico:** O delay de 300s entre envios e OBRIGATORIO e GLOBAL. O worker e o unico processo que envia -- nenhum outro processo pode chamar `evolution.send_text()`.

6. **Flask raw body:** No webhook handler, LER `request.get_data()` ANTES de qualquer `request.get_json()` ou `json.loads()`. O stream so pode ser lido uma vez.

7. **Dois requests para D3:** A Shopify API nao suporta `fulfillment_status=unfulfilled,partial`. Fazer 2 requests separadas e combinar.

8. **SUP05 fail-open:** Se `REVIEW_REQUEST_FILE` estiver vazio ou o ficheiro nao existir, a regra SUP05 e silenciosamente ignorada. NAO bloquear envios por causa de uma feature nao configurada.

---

## Cobertura de Requisitos

| Requisito | Componente(s) | Status |
|-----------|--------------|--------|
| RF01 -- D1 Confirmacao | webhook_handler, messages_d1, message_worker | Coberto |
| RF02 -- D2 Tracking | webhook_handler, messages_d2, message_worker | Coberto |
| RF03 -- D3 Delay | cron_d3, messages_d3, message_worker | Coberto |
| RF04 -- D4 Reorder 3-way | cron_d4, messages_d4, message_worker | Coberto |
| RF05 -- Webhook Server | webhook_handler, webhook_server | Coberto (Flask, nao FastAPI -- DA01) |
| RF06 -- Registo Webhooks | register_webhooks.py | Coberto |
| RF07 -- Fila Anti-Ban | queue_handler, message_worker | Coberto |
| RF08 -- Sent Tracker v2 | sent_tracker (modificado) | Coberto |
| RF09 -- Supressao | suppression (SUP01-SUP05) | Coberto |
| RF10 -- Templates 4 idiomas | messages_d1/d2/d3/d4 | Coberto (28 templates) |
| RF11 -- Enfileiramento horario | queue_handler + message_worker (schedule check) | Coberto |

---

## Pronto para o @dev

O mapeamento esta completo. Todas as funcoes possuem assinaturas com type hints, docstrings com Args/Returns/Raises, e o fluxo de dados entre modulos esta explicito para cada disparo (D1, D2, D3, D4). O @dev pode implementar cada ficheiro seguindo exactamente os contratos definidos sem necessidade de consultar os documentos de input.

---

*Documento gerado por @mapper (Max) em 2026-03-10. Pronto para @dev.*
