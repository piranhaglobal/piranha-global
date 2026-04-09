# Mapeamento Arquitectural — Piranha Supplies Voice

> Versão: 1.0 | Autor: @mapper | Data: 2026-03-30

---

## 1. Visão Geral do Sistema

Sistema de recuperação de carrinho abandonado com IA de voz. Quando um cliente da Piranha Supplies abandona um checkout no Shopify há 7–14 dias, o sistema:

1. Detecta o checkout via Shopify API
2. Cria uma sessão de agente de voz na Ultravox
3. Dispara uma chamada telefónica real via Twilio
4. O agente Bruno conduz a conversa em idioma automático (PT/ES/FR/EN)
5. Regista o resultado e agenda retry se necessário

**Infraestrutura de produção:** VPS 144.91.85.135 | Docker Swarm | domínio `call.piranhasupplies.com`

---

## 2. Árvore de Ficheiros

```
squads/piranha-dev/projects/piranha-supplies-voice/
├── src/
│   ├── main.py                      # Entry point do cron diário
│   ├── config.py                    # Carrega e valida variáveis de ambiente
│   ├── clients/
│   │   ├── shopify.py               # Busca checkouts abandonados + descrições de produto
│   │   ├── twilio.py                # Dispara chamadas telefónicas
│   │   └── ultravox.py              # Cria sessões de agente de voz
│   ├── handlers/
│   │   ├── call_handler.py          # Orquestra o fluxo por checkout
│   │   └── webhook_handler.py       # Servidor Flask — recebe eventos Twilio
│   ├── prompts/
│   │   └── feedback_agent.py        # System prompt do agente Bruno (PT + ES)
│   └── utils/
│       ├── call_tracker.py          # Persiste estado em called.json
│       ├── language_detector.py     # Mapeia país → idioma → voz
│       ├── logger.py                # Configuração de logging
│       ├── product_formatter.py     # Formata produtos para voz natural
│       └── schedule_checker.py      # Janelas de chamadas por timezone do país
├── called.json                      # Estado persistente das chamadas (volume Docker)
├── test_call.py                     # Script de teste manual
├── Dockerfile                       # Imagem Docker do serviço
└── docker-compose.yml               # Definição do stack Docker Swarm
```

---

## 3. Classes e Funções

### `src/config.py` — `Config`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `SHOPIFY_STORE_URL` | str | URL da loja Shopify |
| `SHOPIFY_ACCESS_TOKEN` | str | Token de acesso Admin API |
| `SHOPIFY_API_VERSION` | str | Versão da API (default: `2024-10`) |
| `ULTRAVOX_API_KEY` | str | Chave API Ultravox |
| `ULTRAVOX_VOICE_ID` | str | ID de voz clonada (prioridade 1) |
| `CARTESIA_API_KEY` | str | Chave Cartesia (fallback) |
| `CARTESIA_VOICE_ID` | str | Voice ID Cartesia (lida de `VOICE_ID` no .env) |
| `TWILIO_ACCOUNT_SID` | str | Account SID Twilio |
| `TWILIO_AUTH_TOKEN` | str | Auth Token Twilio |
| `TWILIO_API_KEY_SID` | str | API Key SID (região IE1/Dublin) |
| `TWILIO_API_KEY_SECRET` | str | API Key Secret |
| `TWILIO_FROM_NUMBER` | str | Número de origem em E.164 |
| `TWILIO_EDGE` | str | Edge Twilio (default: `dublin`) |
| `VPS_BASE_URL` | str | URL pública do servidor (ex: `https://call.piranhasupplies.com`) |
| `WEBHOOK_PORT` | int | Porta Flask (default: `5000`) |
| `validate()` | classmethod | Levanta `ValueError` se variável obrigatória ausente |

---

### `src/clients/shopify.py` — `ShopifyClient`

| Método | Assinatura | Descrição |
|--------|-----------|-----------|
| `get_abandoned_checkouts` | `(day_min=8, day_max=7) → list[dict]` | Busca checkouts abertos com telefone na janela de dias |
| `_is_eligible` | `(checkout: dict) → bool` | Filtra: `completed_at` null + tem telefone |
| `_extract_contact` | `(checkout: dict) → dict` | Normaliza campos + busca descrição de cada produto |
| `_get_product_description` | `(product_id, max_chars=400) → str` | GET `/products/{id}.json` → limpa HTML |
| `_clean_html` | `(html, max_chars=400) → str` | Remove tags HTML, normaliza entidades, trunca |
| `_make_request` | `(method, endpoint, **kwargs) → dict` | HTTP com retry 3x + backoff exponencial |

**Saída normalizada de `_extract_contact`:**
```json
{
  "id": "checkout_id",
  "phone": "+351912345678",
  "name": "Sofia",
  "country_code": "PT",
  "products": [
    {"title": "Nome", "vendor": "Marca", "price": "99.00", "description": "Texto limpo..."}
  ],
  "total_price": "99.00",
  "created_at": "2026-03-22T10:00:00Z"
}
```

---

### `src/clients/ultravox.py` — `UltravoxClient`

| Constante/Método | Descrição |
|-----------------|-----------|
| `_TOOL_HANG_UP` | UUID da tool built-in hangUp |
| `_TOOL_QUERY_CORPUS` | UUID da tool built-in queryCorpus (RAG) |
| `_TOOL_LEAVE_VOICEMAIL` | UUID da tool built-in leaveVoicemail |
| `TRANSFER_NUMBER` | Número de suporte para warm transfer (`+351232468548`) |
| `_CORPUS_ID` | UUID da knowledge base Piranha Supplies |
| `create_call(system_prompt, language_hint, voice) → dict` | Cria sessão de voz — retorna `{callId, joinUrl}` |
| `get_call_status(call_id) → str` | `"created"` / `"active"` / `"ended"` / `"failed"` |

**Hierarquia de voz:**
1. `ULTRAVOX_VOICE_ID` → voz nativa clonada (prioridade máxima)
2. `CARTESIA_VOICE_ID` + `CARTESIA_API_KEY` → Cartesia Sonic 3 (fallback 1)
3. `voice` por idioma → voz Ultravox padrão (fallback 2)

**Tools registadas na sessão:**
- `hangUp` — encerra a chamada
- `queryCorpus` — consulta knowledge base RAG da Piranha
- `leaveVoicemail` — deixa mensagem de voz
- `warmTransfer` — transfere com contexto via Twilio Conference → `POST /webhook/warm-transfer`
- `logCallResult` — regista resultado final → `POST /webhook/log-call-result`

**Configurações VAD (ajustadas para Twilio µ-law 8kHz):**
| Parâmetro | Valor | Razão |
|-----------|-------|-------|
| `turnEndpointDelay` | `0.512s` | Pausas de decisão do cliente |
| `minimumTurnDuration` | `0.2s` | Ignora tosse / ruído de fundo |
| `minimumInterruptionDuration` | `0.15s` | Bruno completa frases críticas |
| `frameActivationThreshold` | `0.2` | Reduz falsos positivos do codec |

---

### `src/clients/twilio.py` — `TwilioClient`

| Método | Assinatura | Descrição |
|--------|-----------|-----------|
| `make_call` | `(to_number, twiml_url, status_callback_url) → dict` | POST `/Accounts/{sid}/Calls.json` |
| `build_twiml_url` | `() → str` | `{VPS_BASE_URL}/webhook/twilio/twiml` |
| `build_status_callback_url` | `() → str` | `{VPS_BASE_URL}/webhook/twilio/status` |

---

### `src/handlers/call_handler.py`

| Função | Assinatura | Descrição |
|--------|-----------|-----------|
| `process_checkouts` | `(checkouts: list[dict]) → None` | Processa retries + novos leads sequencialmente |
| `_process_lead_list` | `(checkouts, is_retry) → None` | Itera lista, verifica janela + UE, evita duplicados |
| `process_single` | `(checkout, call_done) → str` | Fluxo completo de uma chamada |
| `_build_call_context` | `(checkout) → dict` | Monta idioma, voz, prompt preenchido |
| `_format_product_details` | `(products, language) → str` | Bloco `{{productDetails}}` com nome exacto + descrição |
| `_format_products` | `(products, language) → str` | Lista natural de produtos para abertura da conversa |
| `_format_value` | `(price_str, language) → str` | Valor monetário em palavras (pt/es/fr/en) |
| `_format_date` | `(date_str, language) → str` | Data ISO → formato natural por idioma |
| `_format_days` | `(date_str, language) → str` | Nº de dias desde abandono |
| `_number_to_pt` | `(n: int) → str` | Inteiro → palavras em português europeu |

**Variáveis partilhadas:**
```python
active_sessions: dict[str, dict]  # call_sid → {join_url, ultravox_call_id, call_done_event}
_sessions_lock: threading.Lock    # protege active_sessions
```

**Fluxo de `process_single`:**
```
checkout → _build_call_context()
         → UltravoxClient.create_call() → join_url + ultravox_call_id
         → active_sessions["pending-{id}"] = {join_url, ...}  ← evita race condition
         → TwilioClient.make_call() → call_sid
         → active_sessions[call_sid] = active_sessions.pop("pending-{id}")
         → call_tracker.mark(join_url=join_url)  ← persistência anti-restart
         → retorna "called"
```

---

### `src/handlers/webhook_handler.py` — Flask

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `GET/POST /webhook/twilio/twiml` | — | Retorna TwiML com join_url para Twilio |
| `POST /webhook/twilio/status` | — | Callbacks de estado (completed/busy/failed/no-answer) |
| `POST /admin/test-call` | — | Dispara chamada de teste em thread separada |
| `POST /webhook/warm-transfer` | — | Cria Twilio Conference e transfere com contexto |
| `POST /webhook/log-call-result` | — | Regista resultado reportado pelo agente Bruno |
| `GET /health` | — | Health check |

**Fallback anti-restart no TwiML handler:**
```
Recebe CallSid
→ Procura em active_sessions (memória)
→ Se não encontrar: call_tracker.get_join_url_by_provider_id(call_sid)
→ Se não encontrar: <Hangup/>
```

**Fluxo de Warm Transfer:**
```
POST /webhook/warm-transfer  (body: {summary}, header: X-UV-Call-Id)
→ Encontra call_sid em active_sessions via ultravox_call_id
→ conference_name = "piranha-wt-{call_sid[-10:]}"
→ POST /Calls.json → TRANSFER_NUMBER com TwiML: Say(summary) + Conference(startOnEnter=true)
→ POST /Calls/{call_sid}.json → TwiML: Conference(startOnEnter=false, endOnExit=true)
→ Cliente e suporte ficam na mesma conferência
```

---

### `src/utils/call_tracker.py`

| Função | Descrição |
|--------|-----------|
| `is_called(checkout_id) → bool` | Verifica se checkout já foi processado |
| `mark(checkout_id, phone, name, status, ..., join_url) → None` | Regista ou actualiza chamada |
| `update_status(provider_call_id, new_status) → None` | Actualiza status pelo Twilio call_sid |
| `mark_for_retry(checkout_id, retry_date) → None` | Agenda 2.ª tentativa (`no_answer_1`) |
| `mark_no_answer_final(checkout_id) → None` | Encerra definitivamente (`no_answer_final`) |
| `get_retry_due(today_str) → list[dict]` | Retorna leads com retry agendado para hoje |
| `get_join_url_by_provider_id(provider_call_id) → str|None` | Recupera join_url para reinício |
| `get_record_by_provider_id(provider_call_id) → tuple|None` | Retorna (checkout_id, record) |
| `get_attempts(checkout_id) → int` | Número de tentativas já realizadas |
| `log_result(provider_call_id, ...) → None` | Regista resultado via logCallResult (por Twilio SID) |
| `log_result_by_ultravox_id(ultravox_call_id, ...) → None` | Regista resultado (por Ultravox ID — fallback) |

**Estrutura de um registo em `called.json`:**
```json
{
  "checkout_id": {
    "phone": "+351912345678",
    "name": "Sofia",
    "status": "called | completed | no_answer_1 | no_answer_final | error",
    "attempts": 1,
    "provider_call_id": "CA...",
    "ultravox_call_id": "uuid",
    "join_url": "wss://...",
    "timestamp": "2026-03-30T10:00:00",
    "checkout_data": {...},
    "completed_at": "2026-03-30T10:05:00",
    "retry_date": "2026-03-31",
    "call_result": {
      "motivo_principal": "preço | esqueceu | portes | concorrente | ...",
      "sub_motivo": "texto livre",
      "resultado": "recuperado | encerrado_sem_interesse | transferido | ...",
      "logged_at": "..."
    }
  }
}
```

---

### `src/utils/schedule_checker.py`

| Função | Descrição |
|--------|-----------|
| `is_calling_hours(country_code) → bool` | Verifica janela no timezone LOCAL do país |
| `get_country_timezone(country_code) → str` | Mapa ISO → IANA timezone (27 países UE) |
| `next_business_day(from_date) → date` | Próximo dia útil (ignora fins de semana) |

**Janelas de chamada:** 11:00–12:30 e 14:00–17:00, seg–sex (hora local do país de destino)

---

### `src/utils/language_detector.py`

| Função | Descrição |
|--------|-----------|
| `get_language(country_code) → str` | PT→"pt", ES→"es", FR→"fr", resto→"en" |
| `get_ultravox_hint(language) → str` | Código languageHint para Ultravox API |
| `get_voice_for_language(language) → str` | pt→PedroPiranha, es→Miguel, fr→Mathieu, en→Matt |

---

### `src/prompts/feedback_agent.py` — `build_system_prompt`

```python
build_system_prompt(
    lead_name: str,
    cart_products: str,
    cart_value: str,
    abandon_date: str,
    days_since_abandon: str,
    product_details: str = "",  # bloco {{productDetails}}
    language: str = "pt",
) → str
```

**Fases do agente Bruno (PT/ES):**

| Fase | Nome | Objectivo |
|------|------|-----------|
| FASE 1 | Abertura | Identifica-se, pergunta se fala com o cliente |
| FASE 2 | Contexto | Menciona o carrinho e o valor em aberto |
| FASE 3 | Qualificação | Descobre o motivo do abandono |
| FASE 4A | Retenção | Oferece ajuda, desconto ou info adicional |
| FASE 4B | Voicemail | Se ninguém atende, deixa mensagem |
| FASE 4C | Questões sobre produto | Disclosure em 3 níveis: categoria → nome exacto → descrição → warmTransfer |
| FASE 5 | Encerramento | logCallResult + hangUp |

**Variáveis do template:**
- `{{nome}}` — primeiro nome do cliente
- `{{produtos}}` — lista natural de produtos (para Fase 1)
- `{{valor}}` — valor total em palavras
- `{{data_abandono}}` — data em formato natural por idioma
- `{{dias_abandono}}` — nº de dias em palavras
- `{{productDetails}}` — bloco de conhecimento técnico dos produtos

---

## 4. Diagrama de Fluxo de Dados

```
CRON (diário)
    │
    ▼
main.py::main()
    │── Config.validate()
    │── is_calling_hours()  ← verifica timezone PT como guarda de entrada
    │
    ▼
ShopifyClient.get_abandoned_checkouts(14, 7)
    │── GET /checkouts.json (7–14 dias atrás, status=open)
    │── Para cada line_item: GET /products/{id}.json → body_html limpo
    │── Retorna lista normalizada com "description" por produto
    │
    ▼
call_handler.process_checkouts(checkouts)
    │── get_retry_due(today) → processa retries primeiro
    │── Para cada checkout:
    │       is_calling_hours(country)  ← verifica timezone LOCAL do país
    │       country in EU_COUNTRIES
    │       call_tracker.is_called(id)
    │
    ▼
call_handler.process_single(checkout, call_done)
    │── _build_call_context() → {language, voice, system_prompt}
    │       _format_product_details() → {{productDetails}}
    │       build_system_prompt() → prompt completo
    │
    ├── UltravoxClient.create_call(system_prompt, language_hint, voice)
    │       POST https://api.ultravox.ai/api/calls
    │       Retorna: {callId, joinUrl: "wss://..."}
    │
    ├── active_sessions["pending-{id}"] = {join_url, ...}
    │
    ├── TwilioClient.make_call(phone, twiml_url, status_callback_url)
    │       POST api.twilio.com/Calls.json
    │       Retorna: {sid: "CA..."}
    │
    ├── active_sessions[call_sid] = ...  (migra de pending-{id})
    │
    └── call_tracker.mark(..., join_url=join_url)  ← persiste para recovery


TWILIO CHAMA O CLIENTE
    │
    ▼ (cliente atende)
GET /webhook/twilio/twiml
    │── Procura call_sid em active_sessions
    │── Fallback: call_tracker.get_join_url_by_provider_id(call_sid)
    │── Retorna TwiML: <Connect><Stream url="wss://..."/></Connect>
    │
    ▼ (Twilio conecta ao WebSocket Ultravox)

AGENTE BRUNO FALA COM O CLIENTE
    │
    ├── [usa queryCorpus] → consulta knowledge base
    │
    ├── [usa warmTransfer(summary)]
    │       POST /webhook/warm-transfer
    │       → Twilio Conference com suporte humano
    │
    ├── [usa logCallResult(motivo, sub_motivo, resultado)]
    │       POST /webhook/log-call-result
    │       → call_tracker.log_result(...)
    │
    └── [usa hangUp] → encerra chamada

POST /webhook/twilio/status (CallStatus: completed/busy/no-answer/failed)
    │── completed → call_tracker.update_status(sid, "completed")
    │── no-answer (tentativa 1) → call_tracker.mark_for_retry(retry_date)
    │── no-answer (tentativa 2) → call_tracker.mark_no_answer_final()
    └── active_sessions.pop(call_sid) → call_done.set()
```

---

## 5. Endpoints — Tabela Resumo

| Endpoint | Método | Quem chama | O que faz |
|----------|--------|-----------|-----------|
| `/webhook/twilio/twiml` | GET/POST | Twilio | Retorna TwiML com WebSocket Ultravox |
| `/webhook/twilio/status` | POST | Twilio | Regista estado final + agenda retry |
| `/webhook/warm-transfer` | POST | Ultravox (tool) | Cria conferência + liga suporte com contexto |
| `/webhook/log-call-result` | POST | Ultravox (tool) | Persiste resultado da chamada |
| `/admin/test-call` | POST | Equipa (manual) | Dispara chamada de teste |
| `/health` | GET | Docker/Traefik | Health check |

---

## 6. Integração com Pixel Agents UI

**Bridge:** `squads/piranha-dev/claude_signal.py`

Escreve eventos em `squads/piranha-dev/data/logs.jsonl` e `state.json`, que o `squad-server.js` (porta 3001) serve via polling para animar os personagens pixel art.

```bash
# Sequência de activação do pipeline
python3 squads/piranha-dev/claude_signal.py --reset
python3 squads/piranha-dev/claude_signal.py @architect "A analisar..."
python3 squads/piranha-dev/claude_signal.py @researcher "A pesquisar..."
python3 squads/piranha-dev/claude_signal.py @mapper "A mapear..."
python3 squads/piranha-dev/claude_signal.py @dev "A implementar..."
python3 squads/piranha-dev/claude_signal.py @qa "A rever..."
python3 squads/piranha-dev/claude_signal.py --status completed
```

---

## 7. Infraestrutura de Produção

| Componente | Valor |
|-----------|-------|
| VPS | 144.91.85.135 |
| Serviço Docker | `piranha-voice_piranha_voice` |
| Imagem | `piranha-voice:latest` |
| Domínio | `call.piranhasupplies.com` |
| Proxy | Traefik (HTTPS automático) |
| Volume | `/opt/piranha-voice-data/called.json` |
| Logs | `docker service logs piranha-voice_piranha_voice -f` |
| Deploy | `push-to-vps.sh` → `docker stack deploy` |

---

## 8. Dependências Externas

| Serviço | Uso | Variável |
|---------|-----|---------|
| Shopify Admin API | Buscar checkouts abandonados + descrições de produto | `SHOPIFY_*` |
| Ultravox API | Criar sessões de agente de voz (LLM + TTS + VAD) | `ULTRAVOX_API_KEY` |
| Twilio | Chamdas telefónicas outbound + webhooks | `TWILIO_*` |
| Cartesia | Voz TTS externa (fallback ao Ultravox nativo) | `CARTESIA_*` |
| Ultravox RAG | Knowledge base de produtos (corpus) | `_CORPUS_ID` |
