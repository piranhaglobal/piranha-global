# Arquitetura: Post Purchase WhatsApp — 4 Disparos

**Projecto:** `post-purchase-wpp`
**Agente:** @architect (Ari)
**Data:** 2026-03-10
**Versao:** 1.0
**Status:** Pronto para @researcher e @mapper
**Base:** Documento `01-analyst-requirements.md` do @analyst

---

## Visao Geral

```
                         SHOPIFY
                           |
              ┌────────────┼────────────┐
              │            │            │
        orders/paid   fulfillments/   REST API
        (webhook)     create          (polling)
              │        (webhook)        │
              │            │            │
              v            v            │
         ┌─────────────────────┐        │
         │   WEBHOOK SERVER    │        │
         │   (Flask, porta     │        │
         │    8000, contínuo)  │        │
         │                     │        │
         │  POST /webhooks/    │        │
         │    orders/paid      │        │
         │  POST /webhooks/    │        │
         │    fulfillments/    │        │
         │    create           │        │
         │  GET /health        │        │
         └────────┬────────────┘        │
                  │                     │
                  │ enqueue             │
                  v                     │
         ┌─────────────────────┐        │
         │   QUEUE (JSON)      │        │
         │   queue.json        │        │
         │   file locking      │        │
         │   prioridade:       │        │
         │   D1 > D2 > D3 > D4 │        │
         └────────┬────────────┘        │
                  │                     │
                  │ dequeue             │
                  v                     │
         ┌─────────────────────┐        │
         │   MESSAGE WORKER    │        │
         │   (daemon contínuo) │        │
         │                     │        │
         │   - delay 300s      │        │
         │   - horário comerc. │        │
         │   - supressão       │        │
         │   - envio WhatsApp  │        │
         └────────┬────────────┘        │
                  │                     │
                  v                     │
         ┌─────────────────────┐        │
         │   EVOLUTION API     │        │
         │   sendText/instance │        │
         └─────────────────────┘        │
                                        │
         ┌─────────────────────┐        │
         │   CRON D3 + D4      │────────┘
         │   (diário 08h05)    │
         │                     │
         │   D3: pedidos 3-5d  │
         │       sem envio     │
         │   D4: pedidos dia25 │
         │       reorder       │
         │                     │
         │   Busca Shopify API │
         │   → enqueue na fila │
         └─────────────────────┘

         ┌─────────────────────┐
         │   SENT TRACKER      │
         │   sent.json (v2)    │
         │   por order_id →    │
         │     dispatches:     │
         │     D1,D2,D3,D4     │
         └─────────────────────┘
```

---

## Decisoes Arquitecturais

### DA01 — Flask (NAO FastAPI)

**Decisao:** Usar Flask para o servidor webhook.

**Justificacao:**
1. O projecto `piranha-supplies-voice` ja usa Flask para webhooks — manter consistencia no ecossistema Piranha
2. O webhook apenas valida HMAC + enfileira — zero processamento pesado, zero beneficio de async
3. Flask e mais simples de operar com systemd na VPS (sem ASGI server extra)
4. O unico componente que envia WhatsApp e o worker daemon (processo separado) — o Flask nunca envia mensagens
5. Menos dependencias: `flask` vs `fastapi` + `uvicorn`

**Impacto:** O @analyst sugeriu FastAPI no RF05. Esta decisao altera para Flask. Endpoints e comportamento sao identicos.

### DA02 — Fila JSON com File Locking (NAO SQLite)

**Decisao:** Fila persistente em ficheiro JSON (`queue.json`) com `fcntl.flock` para concorrencia.

**Justificacao:**
1. Consistente com o padrao actual do projecto (`sent.json`, `cache/consumables.json`)
2. Volume maximo: ~230 mensagens/dia (19h de operacao x 12 msg/hora) — JSON suporta facilmente
3. Facil debug: basta `cat queue.json` para ver estado
4. File locking garante atomicidade entre webhook server e worker daemon
5. SQLite seria over-engineering para < 1000 items/dia

**Risco mitigado:** Se o volume crescer acima de 10.000 items pendentes na fila, migrar para SQLite. O @dev deve implementar a fila com interface abstracta (classe `MessageQueue`) para facilitar troca futura.

### DA03 — 3 Processos na VPS

**Decisao:** Tres processos independentes:

| Processo | Tipo | Gestao | Entry Point |
|----------|------|--------|-------------|
| Webhook Server | Continuo | systemd | `python -m src.webhook_server` |
| Message Worker | Continuo | systemd | `python -m src.worker` |
| Cron D3+D4 | Diario | crontab | `python -m src.cron_dispatcher` |

**Justificacao:**
1. Webhook server deve responder em < 5s (timeout Shopify) — sem bloqueio
2. Worker consome fila a cada 300s — loop continuo com sleep
3. Cron para D3/D4 e mais simples que integrar APScheduler no worker — o cron apenas enfileira, o worker envia
4. Se o worker crashar, o webhook continua a enfileirar (resiliencia)
5. Se o webhook crashar, o cron continua a funcionar

**Alternativa descartada:** Processo unico com APScheduler. Descartado porque misturaria responsabilidades e um crash no scheduler pararia tambem o webhook.

### DA04 — Worker como Unico Emissor

**Decisao:** O message worker daemon e o UNICO processo que envia WhatsApp via Evolution API. Nenhum outro processo pode enviar.

**Justificacao:**
1. Delay de 300s entre envios e GLOBAL — um unico ponto de controlo garante cumprimento
2. Webhook enfileira e responde 200 em < 100ms
3. Cron enfileira e termina em < 30s
4. Worker verifica supressao, horario comercial e delay antes de cada envio

### DA05 — Migracao Backward-Compatible do sent.json

**Decisao:** Funcao `migrate_v1_to_v2()` que converte registos antigos no primeiro load.

**Estrategia:**
```
Formato v1 (actual):
{
  "order_id": {
    "phone": "...", "name": "...", "segment": "A_B",
    "language": "pt", "status": "sent", "timestamp": "..."
  }
}

Formato v2 (novo):
{
  "order_id": {
    "phone": "...", "name": "...", "country_code": "PT",
    "language": "pt",
    "dispatches": {
      "D4": {"status": "sent", "timestamp": "...", "segment": "A_B"}
    }
  }
}
```

**Regras de migracao:**
1. Todo registo v1 existente e tratado como D4 (unico disparo que existia)
2. `segment` move para dentro de `dispatches.D4`
3. `country_code` e inferido do telefone (prefixo) ou defaults para "PT"
4. A migracao acontece UMA vez no primeiro `_load()` que detectar formato v1
5. Apos migracao, salva automaticamente em v2
6. Registos v2 sao reconhecidos pela presenca da chave `dispatches`

---

## Componentes

| Componente | Responsabilidade | Tecnologia | Ficheiro |
|------------|-----------------|------------|----------|
| Webhook Server | Recebe webhooks Shopify, valida HMAC, enfileira D1/D2 | Flask | `src/webhook_server.py` |
| Message Worker | Consome fila, aplica supressao, envia WhatsApp, regista | Python daemon | `src/worker.py` |
| Cron Dispatcher | Busca pedidos D3/D4 na Shopify, enfileira | Python script | `src/cron_dispatcher.py` |
| Message Queue | Fila persistente JSON com prioridade e file locking | JSON + fcntl | `src/utils/queue_manager.py` |
| Sent Tracker v2 | Registo multi-disparo por pedido com migracao | JSON | `src/utils/sent_tracker.py` |
| Suppression Engine | Motor de regras de supressao (SUP01-SUP05) | Python | `src/utils/suppression.py` |
| HMAC Validator | Valida assinatura X-Shopify-Hmac-Sha256 | hmac/hashlib | `src/utils/hmac_validator.py` |
| Webhook Registrar | Regista webhooks na Shopify (setup one-time) | requests | `src/scripts/register_webhooks.py` |
| Shopify Client | Chamadas API Shopify (pedidos, customers, fulfillments) | requests | `src/clients/shopify.py` |
| Evolution Client | Envio WhatsApp + verificacao instancia | requests | `src/clients/evolution.py` |
| D1 Handler | Logica do disparo de confirmacao de pedido | Python | `src/handlers/d1_handler.py` |
| D2 Handler | Logica do disparo de tracking | Python | `src/handlers/d2_handler.py` |
| D3 Handler | Logica do disparo de notificacao de atraso | Python | `src/handlers/d3_handler.py` |
| D4 Handler | Logica do disparo de reorder/cross-sell (refactored) | Python | `src/handlers/d4_handler.py` |
| Templates D1 | 4 idiomas x 3 variantes abertura | Python | `src/prompts/d1_messages.py` |
| Templates D2 | 4 idiomas x 3 variantes abertura | Python | `src/prompts/d2_messages.py` |
| Templates D3 | 4 idiomas x 2 versoes (com/sem link) x 3 variantes | Python | `src/prompts/d3_messages.py` |
| Templates D4 | 4 idiomas x 3 segmentos x 3 variantes | Python | `src/prompts/d4_messages.py` |
| Schedule Checker | Horario comercial + calculo proximo horario valido | pytz | `src/utils/schedule_checker.py` |
| Phone Normalizer | Normalizacao de telefone com DDI | regex | `src/utils/phone_normalizer.py` |
| Language Detector | Mapeamento pais → idioma + DDI | dict | `src/utils/language_detector.py` |
| Config | Carregamento e validacao de .env | dotenv | `src/config.py` |
| Logger | Logging padronizado | stdlib | `src/utils/logger.py` |

---

## Fluxo de Execucao

### Fluxo D1 — Confirmacao de Pedido

```
1. Shopify dispara webhook orders/paid
2. Flask recebe POST /webhooks/orders/paid
3. hmac_validator valida X-Shopify-Hmac-Sha256
   → Se invalido: 401 Unauthorized, log warning
4. Flask extrai dados do pedido (order_id, customer, items, total, phone)
5. Flask cria item de fila:
   {
     "dispatch_type": "D1",
     "priority": 1,
     "order_id": "...",
     "order_name": "#1042",
     "customer_name": "Joao",
     "phone": "+351912345678",
     "country_code": "PT",
     "line_items": [...],
     "total_price": "89.50",
     "currency": "EUR",
     "enqueued_at": "2026-03-10T10:30:00Z"
   }
6. queue_manager.enqueue(item)
7. Flask responde 200 OK (< 100ms total)
8. Worker acorda, dequeue item com maior prioridade
9. Worker verifica supressao (SUP01, SUP02)
   → Se suprimido: mark sent_tracker como "skipped_suppressed", proximo item
10. Worker verifica horario comercial
    → Se fora: item permanece na fila, worker dorme ate 08h00
11. Worker verifica instancia Evolution online
    → Se offline: item volta a fila, worker tenta novamente em 60s
12. d1_handler.process(item) → gera mensagem via d1_messages
13. evolution.send_text(phone_normalizado, mensagem)
14. sent_tracker.mark_dispatch(order_id, "D1", "sent", msg_id)
15. Worker dorme 300s antes do proximo item
```

### Fluxo D2 — Envio + Tracking

```
1. Shopify dispara webhook fulfillments/create
2. Flask recebe POST /webhooks/fulfillments/create
3. hmac_validator valida assinatura
4. Flask verifica se tracking_url esta presente
   → Se ausente: 200 OK + log "fulfillment sem tracking, ignorado"
5. Flask extrai dados (order_id, tracking_number, tracking_url, tracking_company)
6. Flask precisa de dados do pedido (nome, telefone, country_code):
   → Busca order_id no sent_tracker (pode ter dados do D1)
   → Se nao encontrar: enfileira com flag "needs_order_fetch=true"
7. queue_manager.enqueue(item com dispatch_type="D2", priority=2)
8. Flask responde 200 OK
9. Worker dequeue, verifica se precisa fetch de dados do pedido
   → Se needs_order_fetch: shopify.get_order(order_id) para obter nome/telefone
10. Worker verifica supressao (SUP01, SUP02)
11. Worker verifica cooldown de 4h desde D1 (se D1 foi enviado)
12. d2_handler.process(item) → gera mensagem via d2_messages
13. evolution.send_text(phone, mensagem)
14. sent_tracker.mark_dispatch(order_id, "D2", "sent", msg_id)
15. Worker dorme 300s
```

### Fluxo D3 — Notificacao de Atraso (Cron Diario)

```
1. Cron executa cron_dispatcher.py as 08h05 Europe/Lisbon
2. cron_dispatcher verifica horario comercial (redundante mas seguro)
3. cron_dispatcher verifica instancia Evolution online
4. shopify.get_orders_unfulfilled_window(days_min=3, days_max=5)
   → GET /orders.json?created_at_min={-5d}&created_at_max={-3d}
     &financial_status=paid&fulfillment_status=unfulfilled&status=open
5. Para cada pedido elegivel:
   a. Verifica no sent_tracker se D3 ja foi enviado → skip se sim
   b. Re-verifica fulfillment_status em tempo real:
      shopify.get_order(order_id) → se fulfilled, skip + mark "skipped_fulfilled"
   c. Cria item de fila com dispatch_type="D3", priority=3
   d. queue_manager.enqueue(item)
6. cron_dispatcher termina (NAO envia — apenas enfileira)
7. Worker processa normalmente com delay 300s e supressao
```

### Fluxo D4 — Reorder / Cross-sell (Cron Diario)

```
1. Cron executa cron_dispatcher.py as 08h05 (mesmo processo que D3)
2. shopify.get_orders_day_25() (ja implementado)
3. shopify.get_consumable_ids() (ja implementado)
4. Para cada pedido:
   a. Verifica no sent_tracker se D4 ja foi enviado → skip
   b. NOVO: shopify.check_reorder(customer_id, order_date) → skip se recompra
   c. NOVO: Classifica em 3 segmentos:
      - Segmento A: contem consumivel (product_id in consumable_ids)
      - Segmento B: NAO contem consumivel E customer NAO tem tag "wholesale"/"b2b"
      - Segmento C: customer tem tag "wholesale" ou "b2b"
   d. Para B e C: shopify.get_customer(customer_id) para verificar tags
   e. Cria item de fila com dispatch_type="D4", priority=4, segment="A"/"B"/"C"
   f. queue_manager.enqueue(item)
5. cron_dispatcher termina
6. Worker processa normalmente
```

---

## Estrutura de Arquivos

```
post-purchase-wpp/
├── src/
│   ├── __init__.py                          SEM ALTERACAO
│   ├── main.py                              MODIFICAR — renomear logica D4 para cron_dispatcher
│   ├── config.py                            MODIFICAR — adicionar novas variaveis
│   ├── webhook_server.py                    NOVO — servidor Flask para D1/D2
│   ├── worker.py                            NOVO — daemon que consome fila e envia
│   ├── cron_dispatcher.py                   NOVO — cron job que enfileira D3 + D4
│   │
│   ├── clients/
│   │   ├── __init__.py                      SEM ALTERACAO
│   │   ├── shopify.py                       MODIFICAR — novos metodos (get_order, get_orders_unfulfilled, get_customer, check_reorder)
│   │   └── evolution.py                     SEM ALTERACAO
│   │
│   ├── handlers/
│   │   ├── __init__.py                      SEM ALTERACAO
│   │   ├── message_handler.py               MODIFICAR — extrair logica D4, manter como orquestrador legado (deprecated)
│   │   ├── d1_handler.py                    NOVO — handler confirmacao de pedido
│   │   ├── d2_handler.py                    NOVO — handler envio + tracking
│   │   ├── d3_handler.py                    NOVO — handler notificacao de atraso
│   │   └── d4_handler.py                    NOVO — handler reorder/cross-sell (3 segmentos)
│   │
│   ├── prompts/
│   │   ├── __init__.py                      SEM ALTERACAO
│   │   ├── messages.py                      MODIFICAR — deprecated, manter para backward compat temporaria
│   │   ├── d1_messages.py                   NOVO — templates D1 (4 idiomas x 3 variantes)
│   │   ├── d2_messages.py                   NOVO — templates D2 (4 idiomas x 3 variantes)
│   │   ├── d3_messages.py                   NOVO — templates D3 (4 idiomas x 2 versoes x 3 variantes)
│   │   └── d4_messages.py                   NOVO — templates D4 (4 idiomas x 3 segmentos x 3 variantes)
│   │
│   ├── utils/
│   │   ├── __init__.py                      SEM ALTERACAO
│   │   ├── logger.py                        SEM ALTERACAO
│   │   ├── sent_tracker.py                  MODIFICAR — v2 multi-disparo + migracao + indices
│   │   ├── phone_normalizer.py              SEM ALTERACAO
│   │   ├── language_detector.py             SEM ALTERACAO
│   │   ├── schedule_checker.py              MODIFICAR — adicionar next_business_time()
│   │   ├── queue_manager.py                 NOVO — fila persistente com prioridade
│   │   ├── suppression.py                   NOVO — motor de supressao (SUP01-SUP05)
│   │   └── hmac_validator.py                NOVO — validacao HMAC Shopify
│   │
│   └── scripts/
│       └── register_webhooks.py             NOVO — registo one-time de webhooks na Shopify
│
├── cache/
│   └── consumables.json                     SEM ALTERACAO (ja existe)
│
├── sent.json                                MODIFICAR — formato v2 (migracao automatica)
├── queue.json                               NOVO — fila persistente de mensagens
├── .env                                     MODIFICAR — novas variaveis
├── requirements.txt                         MODIFICAR — adicionar flask
├── systemd/
│   ├── piranha-wpp-webhook.service          NOVO — unit file webhook server
│   └── piranha-wpp-worker.service           NOVO — unit file message worker
└── tests/
    ├── __init__.py                          NOVO
    ├── test_hmac_validator.py               NOVO
    ├── test_queue_manager.py                NOVO
    ├── test_suppression.py                  NOVO
    ├── test_sent_tracker_v2.py              NOVO
    ├── test_d1_handler.py                   NOVO
    ├── test_d2_handler.py                   NOVO
    ├── test_d3_handler.py                   NOVO
    └── test_d4_handler.py                   NOVO
```

---

## Especificacao Detalhada por Componente

### COMP01 — webhook_server.py (NOVO)

```python
# Responsabilidade: Servidor Flask que recebe webhooks Shopify para D1 e D2
# Padrao: identico ao webhook_server.py do piranha-supplies-voice

# Funcoes:
# create_app() -> Flask
#   Cria app Flask com 3 rotas:
#     POST /webhooks/orders/paid      -> handle_order_paid()
#     POST /webhooks/fulfillments/create -> handle_fulfillment_create()
#     GET  /health                     -> health_check()

# handle_order_paid(request):
#   1. Ler request body RAW (bytes) antes de parse JSON — necessario para HMAC
#   2. hmac_validator.validate(raw_body, request.headers["X-Shopify-Hmac-Sha256"])
#   3. Parse JSON do body
#   4. Extrair: order_id, order_name, customer_name, phone, country_code,
#              line_items, total_price, currency
#   5. Criar dict de fila (ver formato abaixo)
#   6. queue_manager.enqueue(item)
#   7. return 200 OK

# handle_fulfillment_create(request):
#   1. Validar HMAC
#   2. Parse JSON
#   3. Verificar tracking_url presente — se nao, return 200 + log skip
#   4. Extrair: order_id, tracking_number, tracking_url, tracking_company
#   5. Tentar obter dados do cliente do sent_tracker (pode ter do D1)
#   6. Se nao encontrar, marcar needs_order_fetch=true
#   7. queue_manager.enqueue(item)
#   8. return 200 OK

# health_check():
#   1. Verificar instancia Evolution (evolution.check_instance())
#   2. Ler tamanho da fila (queue_manager.size())
#   3. Ler ultimo envio do sent_tracker
#   4. return JSON: {status, whatsapp_instance, queue_size, last_send, uptime_seconds}

# Entry point (__main__):
#   app = create_app()
#   app.run(host="0.0.0.0", port=Config.SERVER_PORT)
```

### COMP02 — worker.py (NOVO)

```python
# Responsabilidade: Daemon continuo que consome a fila e envia WhatsApp
# Este e o UNICO processo que chama evolution.send_text()

# Fluxo principal (loop infinito):
# while True:
#   1. item = queue_manager.peek()  # le sem remover
#      Se fila vazia: sleep(30), continue
#
#   2. Verificar horario comercial
#      Se fora: calcular proximo horario valido, sleep ate la
#
#   3. Verificar instancia Evolution online
#      Se offline: sleep(60), continue (item permanece na fila)
#
#   4. Se item tem needs_order_fetch=true:
#      dados = shopify.get_order(item["order_id"])
#      Preencher phone, customer_name, country_code no item
#
#   5. Normalizar telefone
#      Se invalido: queue_manager.dequeue(), mark "skipped_no_phone", continue
#
#   6. Verificar supressao (suppression.check_all(phone, order_id, dispatch_type))
#      Se suprimido: queue_manager.dequeue(), mark "skipped_suppressed", continue
#
#   7. Gerar mensagem:
#      handler = {
#        "D1": d1_handler, "D2": d2_handler,
#        "D3": d3_handler, "D4": d4_handler
#      }[item["dispatch_type"]]
#      message = handler.build_message(item)
#
#   8. Enviar: evolution.send_text(phone, message)
#      Se erro: queue_manager.dequeue(), mark "error", continue
#
#   9. queue_manager.dequeue()  # remove da fila
#   10. sent_tracker.mark_dispatch(order_id, dispatch_type, "sent", msg_id)
#   11. time.sleep(Config.SEND_DELAY_SECONDS)  # 300s obrigatorio

# Tratamento de sinais:
# SIGTERM / SIGINT -> finaliza loop graciosamente
# Nao interromper no meio de um envio
```

### COMP03 — cron_dispatcher.py (NOVO)

```python
# Responsabilidade: Cron job diario que busca pedidos elegiveis para D3 e D4
# e os enfileira. NAO envia mensagens — apenas enfileira.

# Funcao principal:
# def main():
#   1. Config.validate()
#   2. Verificar horario comercial (se fora, encerrar)
#   3. Verificar instancia Evolution (se offline, encerrar com warning)
#
#   4. --- D3: Notificacao de Atraso ---
#   orders_d3 = shopify.get_orders_unfulfilled_window(days_min=3, days_max=5)
#   Para cada order:
#     a. Se sent_tracker.is_dispatched(order_id, "D3"): skip
#     b. Re-verificar: shopify.get_order(order_id)
#        Se fulfillment_status == "fulfilled": mark "skipped_fulfilled", skip
#     c. Extrair dados (phone, name, country_code)
#     d. queue_manager.enqueue({dispatch_type: "D3", priority: 3, ...})
#
#   5. --- D4: Reorder/Cross-sell ---
#   orders_d4 = shopify.get_orders_day_25()
#   consumable_ids = shopify.get_consumable_ids()
#   Para cada order:
#     a. Se sent_tracker.is_dispatched(order_id, "D4"): skip
#     b. customer_id = order["customer_id"]
#     c. Se shopify.check_reorder(customer_id, order_created_at): mark "skipped_reordered", skip
#     d. segment = classify_d4(order, consumable_ids, shopify)
#     e. queue_manager.enqueue({dispatch_type: "D4", priority: 4, segment: segment, ...})
#
#   6. Log resumo: "D3: X enfileirados, Y skipped. D4: X enfileirados, Y skipped."

# def classify_d4(order, consumable_ids, shopify) -> str:
#   line_items = order["line_items"]
#   has_consumable = any(item["product_id"] in consumable_ids for item in line_items)
#   if has_consumable:
#     return "A"  # B2C consumiveis
#   # Verificar tags B2B
#   customer = shopify.get_customer(order["customer_id"])
#   tags = (customer.get("tags", "") or "").lower().split(",")
#   tags = [t.strip() for t in tags]
#   if "wholesale" in tags or "b2b" in tags:
#     return "C"  # B2B
#   return "B"  # B2C nao consumiveis
```

### COMP04 — queue_manager.py (NOVO)

```python
# Responsabilidade: Fila persistente em JSON com prioridade e file locking
# Ficheiro: queue.json

# Formato do queue.json:
# {
#   "items": [
#     {
#       "id": "uuid4",
#       "dispatch_type": "D1",
#       "priority": 1,
#       "order_id": "5678901234",
#       "order_name": "#1042",
#       "customer_name": "Joao",
#       "phone": "+351912345678",
#       "country_code": "PT",
#       "data": { ... dados especificos do dispatch ... },
#       "enqueued_at": "2026-03-10T10:30:00Z",
#       "needs_order_fetch": false
#     }
#   ]
# }

# Prioridades:
# 1 = D1 (confirmacao - maior urgencia)
# 2 = D2 (tracking)
# 3 = D3 (delay notification)
# 4 = D4 (reorder - menor urgencia)

# Classe MessageQueue:
#   QUEUE_FILE = Path("queue.json")
#
#   def enqueue(self, item: dict) -> None:
#     """Adiciona item a fila, ordenado por prioridade (menor = mais urgente)."""
#     Com file lock:
#       data = _load()
#       item["id"] = str(uuid4())
#       item["enqueued_at"] = datetime.utcnow().isoformat()
#       data["items"].append(item)
#       data["items"].sort(key=lambda x: (x["priority"], x["enqueued_at"]))
#       _save(data)
#
#   def peek(self) -> dict | None:
#     """Retorna proximo item sem remover. None se fila vazia."""
#     Com file lock:
#       data = _load()
#       return data["items"][0] if data["items"] else None
#
#   def dequeue(self) -> dict | None:
#     """Remove e retorna proximo item da fila."""
#     Com file lock:
#       data = _load()
#       if not data["items"]:
#         return None
#       item = data["items"].pop(0)
#       _save(data)
#       return item
#
#   def size(self) -> int:
#     """Numero de items na fila."""
#
#   def _load(self) -> dict:
#     """Le queue.json com file lock. Retorna {"items": []} se nao existir."""
#
#   def _save(self, data: dict) -> None:
#     """Escreve queue.json com file lock."""

# File locking:
# Usar fcntl.flock(fd, fcntl.LOCK_EX) no Linux/Mac
# O lock e adquirido no open() e libertado no close()
# Padrao:
#   with open(QUEUE_FILE, "r+") as f:
#     fcntl.flock(f, fcntl.LOCK_EX)
#     data = json.load(f)
#     ... operacoes ...
#     f.seek(0)
#     f.truncate()
#     json.dump(data, f)
#     # Lock libertado automaticamente no close
```

### COMP05 — sent_tracker.py v2 (MODIFICAR)

```python
# Responsabilidade: Registo multi-disparo por pedido
# Retrocompativel com formato v1

# Formato v2:
# {
#   "order_id": {
#     "phone": "351912345678",
#     "name": "Joao",
#     "country_code": "PT",
#     "language": "pt",
#     "dispatches": {
#       "D1": {"status": "sent", "timestamp": "...", "msg_id": "3EB0..."},
#       "D2": {"status": "sent", "timestamp": "...", "msg_id": "4FC1...", "tracking_url": "..."},
#       "D3": {"status": "skipped_fulfilled", "timestamp": "..."},
#       "D4": {"status": "sent", "timestamp": "...", "segment": "A", "msg_id": "..."}
#     }
#   }
# }

# Status possiveis por disparo:
# "sent", "pending", "queued", "skipped_fulfilled", "skipped_reordered",
# "skipped_no_phone", "skipped_suppressed", "skipped_cooldown", "error"

# API Publica (v2):
#
# is_dispatched(order_id: str, dispatch_type: str) -> bool
#   """Verifica se um disparo especifico ja foi enviado para o pedido."""
#   return dispatches.get(dispatch_type, {}).get("status") == "sent"
#
# mark_dispatch(order_id: str, dispatch_type: str, status: str,
#               msg_id: str = "", **extra) -> None
#   """Regista um disparo. Cria entrada do pedido se nao existir."""
#
# get_order_data(order_id: str) -> dict | None
#   """Retorna dados do pedido (phone, name, country_code) se existir."""
#
# get_last_send_timestamp(phone: str) -> datetime | None
#   """Retorna timestamp do ultimo envio para este telefone (qualquer pedido)."""
#   Nota: Requer indice invertido phone -> [(order_id, dispatch_type, timestamp)]
#
# count_sends_last_7_days(phone: str) -> int
#   """Conta envios com status="sent" nos ultimos 7 dias para este telefone."""
#
# get_all_dispatches_for_phone(phone: str) -> list[dict]
#   """Lista todos os dispatches para um telefone (para debug)."""

# API Legada (backward compat — deprecated):
# is_sent(order_id: str) -> bool
#   """Verifica se QUALQUER disparo foi enviado. Manter para nao quebrar imports."""
# mark(order_id, phone, name, segment, language, status) -> None
#   """Wrapper que chama mark_dispatch com D4. Manter para nao quebrar imports."""

# Indice invertido por telefone:
# Construido em memoria no _load():
# _phone_index: dict[str, list[tuple[str, str, str]]]
# Mapeia telefone -> [(order_id, dispatch_type, timestamp), ...]
# Reconstruido a cada _load() — aceitavel para < 50k registos

# Migracao v1 -> v2:
# def _migrate_v1_to_v2(data: dict) -> dict:
#   Para cada order_id, entry em data:
#     Se "dispatches" in entry: ja v2, skip
#     old_segment = entry.pop("segment", "A_B")
#     old_status = entry.pop("status", "sent")
#     old_timestamp = entry.pop("timestamp", "")
#     entry["country_code"] = entry.get("country_code", "PT")
#     entry["dispatches"] = {
#       "D4": {
#         "status": old_status,
#         "timestamp": old_timestamp,
#         "segment": old_segment
#       }
#     }
#   return data
```

### COMP06 — suppression.py (NOVO)

```python
# Responsabilidade: Motor de regras de supressao

# def check_all(phone: str, order_id: str, dispatch_type: str,
#               shopify: ShopifyClient = None, order_data: dict = None) -> tuple[bool, str]:
#   """
#   Executa todas as regras de supressao aplicaveis.
#   Returns:
#     (False, "") se nao suprimido — pode enviar
#     (True, "SUP01") se suprimido — com codigo da regra
#   """
#   regras = [
#     _check_sup01_cooldown_4h,      # sempre
#     _check_sup02_max_3_7days,      # sempre
#     _check_sup04_fulfilled,        # so D3
#     _check_sup03_reorder,          # so D4
#     _check_sup05_review_request,   # sempre (graceful skip se nao configurado)
#   ]
#   for regra in regras:
#     suppressed, code = regra(phone, order_id, dispatch_type, shopify, order_data)
#     if suppressed:
#       return (True, code)
#   return (False, "")

# SUP01 — Max 1 WhatsApp por telefone a cada 4 horas
# def _check_sup01_cooldown_4h(phone, ...) -> tuple[bool, str]:
#   last_send = sent_tracker.get_last_send_timestamp(phone)
#   if last_send and (now - last_send) < timedelta(hours=4):
#     return (True, "SUP01")
#   return (False, "")

# SUP02 — Max 3 mensagens automaticas por telefone em 7 dias
# def _check_sup02_max_3_7days(phone, ...) -> tuple[bool, str]:
#   count = sent_tracker.count_sends_last_7_days(phone)
#   if count >= 3:
#     return (True, "SUP02")
#   return (False, "")

# SUP03 — Verificar recompra antes de D4
# def _check_sup03_reorder(phone, order_id, dispatch_type, shopify, order_data) -> tuple[bool, str]:
#   if dispatch_type != "D4":
#     return (False, "")
#   # shopify.check_reorder() ja e chamado no cron_dispatcher
#   # Esta verificacao aqui e redundante mas serve como safety net
#   # Se order_data inclui customer_id e created_at:
#   if shopify and order_data:
#     has_reorder = shopify.check_reorder(customer_id, created_at)
#     if has_reorder:
#       return (True, "SUP03")
#   return (False, "")

# SUP04 — D3 skip se ja fulfilled
# def _check_sup04_fulfilled(phone, order_id, dispatch_type, shopify, ...) -> tuple[bool, str]:
#   if dispatch_type != "D3":
#     return (False, "")
#   # Re-verificacao em tempo real (safety net — cron ja verifica)
#   if shopify:
#     order = shopify.get_order(order_id)
#     if order.get("fulfillment_status") == "fulfilled":
#       return (True, "SUP04")
#   return (False, "")

# SUP05 — Cooldown Review Request
# def _check_sup05_review_request(phone, ...) -> tuple[bool, str]:
#   # Implementacao provisoria: ficheiro review_requests.json
#   # Formato: { "phone": "timestamp_activacao" }
#   # Se ficheiro nao existir ou variavel nao configurada: skip regra (nao bloquear)
#   review_file = Path(Config.REVIEW_REQUEST_FILE) if Config.REVIEW_REQUEST_FILE else None
#   if not review_file or not review_file.exists():
#     return (False, "")
#   data = json.loads(review_file.read_text())
#   activation = data.get(phone)
#   if activation:
#     activation_dt = datetime.fromisoformat(activation)
#     if (now - activation_dt) < timedelta(hours=24):
#       return (True, "SUP05")
#   return (False, "")
```

### COMP07 — hmac_validator.py (NOVO)

```python
# Responsabilidade: Validar assinatura HMAC-SHA256 dos webhooks Shopify

# import hmac, hashlib, base64

# def validate(raw_body: bytes, hmac_header: str) -> bool:
#   """
#   Valida que o webhook foi enviado pela Shopify.
#   Args:
#     raw_body: corpo do request em bytes (antes de parse JSON)
#     hmac_header: valor do header X-Shopify-Hmac-Sha256
#   Returns:
#     True se assinatura valida
#   """
#   secret = Config.SHOPIFY_WEBHOOK_SECRET.encode("utf-8")
#   computed = base64.b64encode(
#     hmac.new(secret, raw_body, hashlib.sha256).digest()
#   ).decode("utf-8")
#   return hmac.compare_digest(computed, hmac_header)

# IMPORTANTE: No Flask, ler request.get_data() ANTES de request.get_json()
# porque get_json() consome o stream. Guardar raw body primeiro.
```

### COMP08 — schedule_checker.py (MODIFICAR)

```python
# Adicionar ao ficheiro existente:

# def next_business_time(timezone: str = "Europe/Lisbon") -> datetime:
#   """
#   Calcula o proximo horario comercial valido.
#   Se agora e horario valido, retorna agora.
#   Se fora do horario, retorna 08h00 do proximo dia util.
#
#   Exemplos:
#     Sabado 21h00 -> Segunda 08h00
#     Domingo 10h00 -> Segunda 08h00
#     Terca 03h00 -> Terca 08h00
#     Quarta 15h00 -> Quarta 15h00 (agora mesmo)
#
#   Returns:
#     datetime aware (timezone Europe/Lisbon)
#   """

# def seconds_until_business_hours(timezone: str = "Europe/Lisbon") -> int:
#   """
#   Retorna 0 se agora e horario comercial.
#   Retorna segundos ate o proximo horario valido se fora.
#   Usado pelo worker para sleep preciso.
#   """
```

### COMP09 — shopify.py (MODIFICAR)

```python
# Novos metodos a adicionar ao ShopifyClient existente:

# def get_order(self, order_id: str) -> dict:
#   """
#   Busca um pedido especifico pelo ID.
#   Usado para re-verificacao de fulfillment_status (D3) e fetch de dados (D2).
#   Returns:
#     dict com campos normalizados + fulfillment_status + customer_id + created_at
#   """
#   raw = self._make_request("GET", f"/orders/{order_id}.json")
#   order = raw.get("order", {})
#   return {
#     "id": str(order.get("id", "")),
#     "name": order.get("name", ""),
#     "fulfillment_status": order.get("fulfillment_status"),
#     "customer_id": str((order.get("customer") or {}).get("id", "")),
#     "customer_name": (order.get("customer") or {}).get("first_name", "cliente"),
#     "phone": order.get("phone") or (order.get("customer") or {}).get("phone", ""),
#     "country_code": ((order.get("shipping_address") or {}).get("country_code") or "PT").upper(),
#     "line_items": [
#       {"product_id": i.get("product_id"), "title": i.get("title", ""),
#        "quantity": i.get("quantity", 1), "price": i.get("price", "0")}
#       for i in order.get("line_items", [])
#     ],
#     "total_price": order.get("total_price", "0"),
#     "currency": order.get("currency", "EUR"),
#     "created_at": order.get("created_at", ""),
#   }

# def get_orders_unfulfilled_window(self, days_min: int = 3, days_max: int = 5) -> list[dict]:
#   """
#   Busca pedidos pagos criados entre days_max e days_min dias atras,
#   que ainda NAO foram enviados (unfulfilled ou partial).
#   Usado pelo D3.
#   """
#   now = datetime.now(timezone.utc)
#   created_at_min = (now - timedelta(days=days_max)).strftime("%Y-%m-%dT%H:%M:%SZ")
#   created_at_max = (now - timedelta(days=days_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
#   raw = self._make_request("GET", "/orders.json", params={
#     "created_at_min": created_at_min,
#     "created_at_max": created_at_max,
#     "financial_status": "paid",
#     "fulfillment_status": "unfulfilled",
#     "status": "open",
#     "limit": 250,
#   })
#   orders = raw.get("orders", [])
#   # Incluir tambem partial:
#   raw_partial = self._make_request("GET", "/orders.json", params={
#     "created_at_min": created_at_min,
#     "created_at_max": created_at_max,
#     "financial_status": "paid",
#     "fulfillment_status": "partial",
#     "status": "open",
#     "limit": 250,
#   })
#   orders.extend(raw_partial.get("orders", []))
#   return [self._extract_order_extended(o) for o in orders]

# def get_customer(self, customer_id: str) -> dict:
#   """
#   Busca dados do customer (incluindo tags para classificacao B2B).
#   Returns:
#     dict com id, first_name, tags (string separada por virgula)
#   """
#   raw = self._make_request("GET", f"/customers/{customer_id}.json")
#   customer = raw.get("customer", {})
#   return {
#     "id": str(customer.get("id", "")),
#     "first_name": customer.get("first_name", ""),
#     "tags": customer.get("tags", ""),
#     "phone": customer.get("phone", ""),
#   }

# def check_reorder(self, customer_id: str, since_date: str) -> bool:
#   """
#   Verifica se o customer fez nova compra desde since_date.
#   Args:
#     customer_id: ID do customer Shopify
#     since_date: data ISO do pedido original
#   Returns:
#     True se existe pedido mais recente pago
#   """
#   raw = self._make_request("GET", "/orders.json", params={
#     "customer_id": customer_id,
#     "created_at_min": since_date,
#     "financial_status": "paid",
#     "status": "any",
#     "limit": 2,  # 2 porque o primeiro pode ser o proprio pedido
#   })
#   orders = raw.get("orders", [])
#   # Filtrar o proprio pedido
#   return len(orders) > 1

# def _extract_order_extended(self, order: dict) -> dict:
#   """
#   Versao estendida do _extract_order que inclui campos extras
#   necessarios para D1/D2/D3.
#   """
#   base = self._extract_order(order)
#   base["customer_id"] = str((order.get("customer") or {}).get("id", ""))
#   base["order_name"] = order.get("name", "")
#   base["total_price"] = order.get("total_price", "0")
#   base["currency"] = order.get("currency", "EUR")
#   base["fulfillment_status"] = order.get("fulfillment_status")
#   base["created_at"] = order.get("created_at", "")
#   base["line_items_extended"] = [
#     {
#       "product_id": i.get("product_id"),
#       "title": i.get("title", ""),
#       "quantity": i.get("quantity", 1),
#       "price": i.get("price", "0"),
#     }
#     for i in order.get("line_items", [])
#   ]
#   return base
```

### COMP10 — config.py (MODIFICAR)

```python
# Novas variaveis a adicionar:

# SHOPIFY_WEBHOOK_SECRET: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
# WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "")
# SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
# EDUCATIONAL_CONTENT_URL: str = os.getenv("EDUCATIONAL_CONTENT_URL", "")
# REVIEW_REQUEST_FILE: str = os.getenv("REVIEW_REQUEST_FILE", "")

# Actualizar _REQUIRED para incluir SHOPIFY_WEBHOOK_SECRET quando
# webhook server estiver activo. Sugestao: dois modos de validacao:
#
# _REQUIRED_BASE = [
#   "SHOPIFY_STORE_URL", "SHOPIFY_ACCESS_TOKEN",
#   "EVOLUTION_API_URL", "EVOLUTION_API_KEY", "EVOLUTION_INSTANCE",
# ]
# _REQUIRED_WEBHOOK = _REQUIRED_BASE + ["SHOPIFY_WEBHOOK_SECRET"]
#
# @classmethod
# def validate(cls, mode: str = "base") -> None:
#   required = cls._REQUIRED_WEBHOOK if mode == "webhook" else cls._REQUIRED_BASE
#   missing = [k for k in required if not getattr(cls, k)]
#   if missing:
#     raise ValueError(f"Variaveis ausentes: {missing}")
```

### COMP11 — Handlers D1-D4 (NOVOS + MODIFICAR)

```python
# Cada handler tem a mesma assinatura:

# class DxHandler:
#   def __init__(self, shopify: ShopifyClient = None):
#     self.shopify = shopify
#
#   def build_message(self, queue_item: dict) -> str:
#     """
#     Gera a mensagem final para envio.
#     Args:
#       queue_item: item da fila com todos os dados do pedido
#     Returns:
#       string pronta para evolution.send_text()
#     """
#
#   def get_phone(self, queue_item: dict) -> str | None:
#     """Extrai e normaliza telefone do item."""

# --- d1_handler.py ---
# build_message extrai:
#   - customer_name, order_name, line_items, total_price, currency, country_code
#   - language = get_language(country_code)
#   - message = d1_messages.build(language, customer_name, order_name, items, total, currency)

# --- d2_handler.py ---
# build_message extrai:
#   - customer_name, tracking_url, tracking_number, tracking_company, country_code
#   - language = get_language(country_code)
#   - message = d2_messages.build(language, customer_name, tracking_url, tracking_company)

# --- d3_handler.py ---
# build_message extrai:
#   - customer_name, order_name, country_code
#   - language = get_language(country_code)
#   - has_edu_link = bool(Config.EDUCATIONAL_CONTENT_URL)
#   - message = d3_messages.build(language, customer_name, order_name, edu_url=Config.EDUCATIONAL_CONTENT_URL)

# --- d4_handler.py ---
# REFACTOR do message_handler.py actual
# Mudancas:
#   1. Segmentacao 3-way: A, B, C (em vez de A_B, C)
#   2. Remover emojis de todos os templates
#   3. Adicionar assinatura "-- Piranha Supplies"
#   4. build_message:
#      segment = queue_item["segment"]  # ja classificado pelo cron_dispatcher
#      language = get_language(country_code)
#      if segment == "A":
#        message = d4_messages.build_segment_a(language, name, consumable_titles)
#      elif segment == "B":
#        message = d4_messages.build_segment_b(language, name)
#      elif segment == "C":
#        message = d4_messages.build_segment_c(language, name)
```

### COMP12 — Templates de Mensagem (NOVOS)

```python
# Estrutura comum a todos os ficheiros de template:

# Cada template tem 3 variantes de abertura para anti-ban
# Seleccao aleatoria (random.choice) por envio

# VARIANTES_ABERTURA = {
#   "pt": ["Ola {name}", "Bom dia {name}", "{name}, tudo bem"],
#   "es": ["Hola {name}", "Buenos dias {name}", "{name}, que tal"],
#   "fr": ["Bonjour {name}", "{name}, bonjour", "Cher {name}"],
#   "en": ["Hi {name}", "Hello {name}", "{name}, good day"],
# }

# ASSINATURA = "\n\n-- Piranha Supplies"

# REGRAS GLOBAIS DE COPY:
# - ZERO emojis
# - Tom profissional, tecnico, confiavel
# - Personalizar com primeiro nome
# - Assinatura final obrigatoria
# - Variacao de abertura para anti-ban

# --- d1_messages.py ---
# def build(language, name, order_name, items, total, currency) -> str:
#   abertura = random.choice(VARIANTES_ABERTURA[language])
#   items_text = "\n".join(f"  - {i['title']} (x{i['quantity']})" for i in items)
#   # Corpo: confirmar pedido, listar items, total, proximo passo (tracking)
#   # Fechar com assinatura

# --- d2_messages.py ---
# def build(language, name, tracking_url, tracking_company) -> str:
#   # Confirmar envio, tracking URL, transportadora, prazo estimado

# --- d3_messages.py ---
# def build(language, name, order_name, edu_url="") -> str:
#   # Se edu_url: versao com link educativo
#   # Se nao: versao fallback mais curta

# --- d4_messages.py ---
# def build_segment_a(language, name, consumable_titles) -> str:
#   # Reposicao de stock (consumiveis comprados)
# def build_segment_b(language, name) -> str:
#   # Cross-sell consumiveis (nao comprou consumiveis)
# def build_segment_c(language, name) -> str:
#   # B2B: reposicao com tom profissional B2B
```

### COMP13 — register_webhooks.py (NOVO)

```python
# Script de setup one-time para registar webhooks na Shopify

# def main():
#   shopify = ShopifyClient()
#   base_url = Config.WEBHOOK_BASE_URL.rstrip("/")
#
#   webhooks_to_register = [
#     {"topic": "orders/paid", "address": f"{base_url}/webhooks/orders/paid"},
#     {"topic": "fulfillments/create", "address": f"{base_url}/webhooks/fulfillments/create"},
#   ]
#
#   # 1. Listar webhooks existentes
#   existing = shopify._make_request("GET", "/webhooks.json")
#   existing_topics = {w["topic"]: w["id"] for w in existing.get("webhooks", [])}
#
#   for wh in webhooks_to_register:
#     if wh["topic"] in existing_topics:
#       logger.info(f"Webhook {wh['topic']} ja existe (id={existing_topics[wh['topic']]})")
#       continue
#     result = shopify._make_request("POST", "/webhooks.json", json={
#       "webhook": {
#         "topic": wh["topic"],
#         "address": wh["address"],
#         "format": "json",
#       }
#     })
#     webhook_id = result.get("webhook", {}).get("id")
#     logger.info(f"Webhook registado: {wh['topic']} -> id={webhook_id}")
```

---

## Formato do Item de Fila (Contrato)

Todos os dispatches usam o mesmo formato de item na fila. Campos especificos por dispatch ficam em `data`:

```json
{
  "id": "a1b2c3d4-uuid",
  "dispatch_type": "D1",
  "priority": 1,
  "order_id": "5678901234",
  "order_name": "#1042",
  "customer_name": "Joao",
  "customer_id": "1234567890",
  "phone": "+351912345678",
  "country_code": "PT",
  "needs_order_fetch": false,
  "enqueued_at": "2026-03-10T10:30:00Z",
  "data": {
    "line_items": [
      {"product_id": 111222333, "title": "Piranha Cartridge Needles", "quantity": 2, "price": "24.50"}
    ],
    "total_price": "89.50",
    "currency": "EUR",
    "tracking_url": null,
    "tracking_number": null,
    "tracking_company": null,
    "segment": null
  }
}
```

**Campos especificos por dispatch:**

| Campo em `data` | D1 | D2 | D3 | D4 |
|-----------------|----|----|----|----|
| line_items | sim | nao | nao | sim (para titulo consumiveis) |
| total_price | sim | nao | nao | nao |
| currency | sim | nao | nao | nao |
| tracking_url | nao | sim | nao | nao |
| tracking_number | nao | sim | nao | nao |
| tracking_company | nao | sim | nao | nao |
| segment | nao | nao | nao | sim (A/B/C) |
| consumable_titles | nao | nao | nao | sim (seg A) |

---

## Dependencias (requirements.txt)

```
requests==2.31.0
python-dotenv==1.0.0
pytz==2024.1
flask==3.0.3
```

**Nota:** `flask==3.0.3` e a unica dependencia nova. Nao e necessario `uvicorn` nem `fastapi`. Os modulos `hmac`, `hashlib`, `base64`, `fcntl`, `uuid`, `json`, `signal` sao todos stdlib.

---

## Configuracao (.env necessario)

```bash
# ── SHOPIFY ──────────────────────────────────────────────
SHOPIFY_STORE_URL=piranhasupplies.myshopify.com    # Dominio Shopify (sem https://)
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx                    # Token de acesso Admin API
SHOPIFY_API_VERSION=2024-10                         # Versao da API (nao alterar)
SHOPIFY_CONSUMABLES_HANDLE=consumables-and-hygiene  # Handle da coleccao consumiveis
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx                  # NOVO — Secret para validar HMAC dos webhooks

# ── EVOLUTION API ────────────────────────────────────────
EVOLUTION_API_URL=https://evolution.dominio.com     # URL base da Evolution API
EVOLUTION_API_KEY=xxxxx                              # API key
EVOLUTION_INSTANCE=piranha-instance                  # Nome da instancia WhatsApp

# ── SERVIDOR WEBHOOK (NOVO) ─────────────────────────────
WEBHOOK_BASE_URL=https://webhook.dominio.com        # URL publica acessivel pela Shopify
SERVER_PORT=8000                                     # Porta do Flask (atras de reverse proxy)

# ── REGRAS DE ENVIO ─────────────────────────────────────
SEND_DELAY_SECONDS=300                               # Delay entre envios (NAO ALTERAR — conta foi banida)

# ── CONTEUDO OPCIONAL (NOVO) ────────────────────────────
EDUCATIONAL_CONTENT_URL=                             # URL conteudo educativo D3 (vazio = fallback sem link)
REVIEW_REQUEST_FILE=                                 # Path ficheiro de review requests activos (vazio = skip SUP05)
```

---

## Infraestrutura VPS

### Systemd — Webhook Server

Ficheiro: `/etc/systemd/system/piranha-wpp-webhook.service`

```ini
[Unit]
Description=Piranha Supplies - Post Purchase WhatsApp Webhook Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projetos/post-purchase-wpp
ExecStart=/home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.webhook_server
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/projetos/post-purchase-wpp/.env

[Install]
WantedBy=multi-user.target
```

### Systemd — Message Worker

Ficheiro: `/etc/systemd/system/piranha-wpp-worker.service`

```ini
[Unit]
Description=Piranha Supplies - Post Purchase WhatsApp Message Worker
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projetos/post-purchase-wpp
ExecStart=/home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.worker
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/projetos/post-purchase-wpp/.env

[Install]
WantedBy=multi-user.target
```

### Crontab

```bash
# Post Purchase WhatsApp — D3 + D4 dispatcher
# Executa diariamente as 08h05 Europe/Lisbon (seg-sab)
# O proprio script verifica horario comercial e dia da semana
5 8 * * 1-6 cd /home/ubuntu/projetos/post-purchase-wpp && /home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.cron_dispatcher >> /var/log/piranha-wpp-cron.log 2>&1
```

### Nginx Reverse Proxy (referencia)

```nginx
server {
    listen 443 ssl;
    server_name webhook.dominio.com;

    ssl_certificate /etc/letsencrypt/live/webhook.dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webhook.dominio.com/privkey.pem;

    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## Ordem de Implementacao Recomendada

O @dev deve seguir esta ordem para minimizar dependencias e permitir testes incrementais:

| Fase | Componentes | Dependencias | Testavel Isoladamente |
|------|------------|-------------|----------------------|
| 1 | `config.py` (novas vars) + `hmac_validator.py` | Nenhuma | Sim (teste unitario HMAC) |
| 2 | `queue_manager.py` | Nenhuma | Sim (teste unitario enqueue/dequeue) |
| 3 | `sent_tracker.py` v2 + migracao | Nenhuma | Sim (teste migracao + API v2) |
| 4 | `suppression.py` | sent_tracker v2 | Sim (mock sent_tracker) |
| 5 | `schedule_checker.py` (next_business_time) | Nenhuma | Sim (teste com datas fixas) |
| 6 | `shopify.py` (novos metodos) | Nenhuma | Sim (mock HTTP) |
| 7 | Templates `d1_messages.py` a `d4_messages.py` | Nenhuma | Sim (teste output strings) |
| 8 | Handlers `d1_handler.py` a `d4_handler.py` | Templates + shopify | Sim (mock) |
| 9 | `webhook_server.py` (Flask) | hmac_validator + queue_manager | Sim (Flask test client) |
| 10 | `cron_dispatcher.py` | shopify + queue_manager + sent_tracker | Sim (mock shopify) |
| 11 | `worker.py` | Todos os anteriores | Teste integracao |
| 12 | `register_webhooks.py` | shopify client | Teste manual na Shopify |
| 13 | `systemd/` + crontab | Infraestrutura | Teste na VPS |

---

## Pontos de Qualidade (Quality Gates)

### Funcionalidade

- [ ] QG01: Webhook orders/paid recebido e enfileirado com HMAC valido
- [ ] QG02: Webhook fulfillments/create recebido e enfileirado (com tracking)
- [ ] QG03: Webhook sem tracking URL retorna 200 mas NAO enfileira
- [ ] QG04: HMAC invalido retorna 401
- [ ] QG05: Worker envia D1 com mensagem correcta em 4 idiomas
- [ ] QG06: Worker envia D2 com tracking URL na mensagem
- [ ] QG07: Cron D3 enfileira apenas pedidos 3-5 dias sem fulfillment
- [ ] QG08: Cron D3 NAO enfileira pedidos ja fulfilled
- [ ] QG09: Cron D4 classifica correctamente segmentos A, B, C
- [ ] QG10: Cron D4 skip se cliente ja fez recompra (SUP03)
- [ ] QG11: D4 segmento C identifica correctamente tags "wholesale"/"b2b"

### Anti-Ban

- [ ] QG12: Delay de 300s entre envios consecutivos (cronometrar)
- [ ] QG13: Delay de 1200ms no payload Evolution (campo `delay`)
- [ ] QG14: Variacao de abertura nas mensagens (nao repetitivo)
- [ ] QG15: Max 12 mensagens/hora (resultado do delay 300s)

### Supressao

- [ ] QG16: SUP01 — Mesmo telefone bloqueado se < 4h desde ultimo envio
- [ ] QG17: SUP02 — Telefone bloqueado se >= 3 envios nos ultimos 7 dias
- [ ] QG18: SUP03 — D4 skip se recompra detectada
- [ ] QG19: SUP04 — D3 skip se fulfillment confirmado em tempo real
- [ ] QG20: SUP05 — Skip se review request activo < 24h (ou graceful skip se nao configurado)

### Horario Comercial

- [ ] QG21: Webhook fora do horario enfileira normalmente (nao descarta)
- [ ] QG22: Worker NAO envia fora do horario — dorme ate proximo dia util
- [ ] QG23: Sabado 21h00 → reagenda para Segunda 08h00
- [ ] QG24: Domingo qualquer hora → reagenda para Segunda 08h00

### Persistencia e Resiliencia

- [ ] QG25: queue.json sobrevive a restart do webhook server
- [ ] QG26: queue.json sobrevive a restart do worker
- [ ] QG27: sent.json v1 migra correctamente para v2
- [ ] QG28: File locking funciona entre webhook server e worker simultaneos
- [ ] QG29: Worker trata SIGTERM graciosamente (nao corta envio no meio)

### Backward Compatibility

- [ ] QG30: sent.json com registos v1 e lido correctamente
- [ ] QG31: Registos v1 migrados sao marcados como D4
- [ ] QG32: API legada is_sent() e mark() continuam a funcionar

### Healthcheck

- [ ] QG33: GET /health retorna JSON com status, queue_size, whatsapp_instance
- [ ] QG34: Health check reflecte estado real da instancia Evolution

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| Ban do numero WhatsApp | Media | Critico | Delay 300s + variacao de copy + max 12 msg/h |
| Webhooks Shopify nao chegam | Baixa | Alto | Retry automatico Shopify (48h) + healthcheck + logs |
| File lock deadlock | Baixa | Alto | Timeout no flock (10s) + recovery automatico |
| queue.json corrompido | Baixa | Alto | Backup antes de cada write + try/except no load |
| Worker e webhook escrevem queue.json simultaneamente | Media | Medio | fcntl.flock garante exclusao mutua |
| Volume > 230 msg/dia | Baixa | Medio | Com 300s delay e 19h operacao: tecto fisico impossivel de ultrapassar |
| sent.json cresce muito | Media | Baixo | Rotacao mensal ou migracao SQLite se > 10k |
| Evolution API indisponivel | Baixa | Alto | Worker re-tenta em 60s, item permanece na fila |
| Fulfillment sem tracking | Media | Baixo | D2 ignora graciosamente — documentado e logado |
| Review Request interface indefinida | Alta | Baixo | SUP05 implementado como ficheiro JSON — extensivel depois |

---

## Notas para o @mapper

1. **Diagrama de dependencias entre ficheiros** — mapear imports para garantir zero dependencias circulares
2. **Fluxo de dados completo** para cada dispatch (D1 a D4) — entrada, transformacoes, saida
3. **Interfaces entre processos** — webhook_server e worker comunicam APENAS via queue.json
4. **Shared state** — sent.json e acedido por worker (escrita) e cron_dispatcher (leitura para skip). Verificar que file locking cobre ambos os acessos.

## Notas para o @researcher

1. **Flask request.get_data()** — confirmar que funciona antes de request.get_json() para preservar raw body (necessario para HMAC)
2. **fcntl.flock** — confirmar comportamento em Linux (VPS Ubuntu) — Mac tem variantes
3. **Shopify webhook retry policy** — documentar exactamente quando a Shopify re-envia (48h, quantas tentativas)
4. **fulfillments/create webhook** — confirmar schema exacto do payload (campos tracking_url, tracking_company)

## Notas para o @dev

1. **NAO reescrever** — construir SOBRE o codigo existente. `message_handler.py` e `messages.py` ficam deprecated mas funcionais.
2. **main.py** actual passa a ser wrapper que chama `cron_dispatcher.main()` para manter compatibilidade com o crontab existente durante a transicao.
3. **Todos os templates** devem terminar com `\n\n-- Piranha Supplies` (duas linhas em branco antes da assinatura).
4. **random.choice** para variantes de abertura — usar `random.seed()` baseado em order_id para reprodutibilidade em debug.
5. **Log format** deve incluir dispatch_type no prefixo: `[D1] Pedido #1042 | phone=... | status=sent`

---

*Blueprint gerado por @architect (Ari) em 2026-03-10. Pronto para @researcher e @mapper.*
