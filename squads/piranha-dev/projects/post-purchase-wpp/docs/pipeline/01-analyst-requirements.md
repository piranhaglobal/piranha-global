# Levantamento de Requisitos -- Post Purchase WhatsApp (4 Disparos)

**Projecto:** `post-purchase-wpp`
**Agente:** @analyst (Ana)
**Data:** 2026-03-10
**Versao:** 1.0
**Status:** Pronto para @architect

---

## 1. Objetivo de Negocio

Expandir o sistema actual de pos-compra WhatsApp -- que hoje opera apenas com um unico disparo no dia 25 (D4 -- Reorder/Cross-sell) -- para um fluxo completo de 4 disparos que cubra toda a jornada pos-compra do cliente:

| Disparo | Nome | Gatilho | Objectivo |
|---------|------|---------|-----------|
| D1 | Confirmacao de Pedido | Pagamento confirmado (orders/paid) | Reforcar confianca, resumir pedido, informar proximos passos |
| D2 | Envio + Tracking | Fulfillment criado com tracking | Notificar envio com URL de rastreio e prazo estimado |
| D3 | Notificacao de Atraso | 3-5 dias apos compra, se NAO enviado | Dar update proactivo, manter confianca, conteudo educativo opcional |
| D4 | Reorder / Cross-sell | Dia 25 apos compra | Incentivar recompra (consumiveis) ou cross-sell (nao consumiveis) |

**Resultado esperado:** Aumento de recompra, reducao de tickets de suporte sobre status do pedido, melhoria da experiencia pos-compra e retencao de clientes.

**Restricao critica:** Todo o fluxo opera via Shopify API + Evolution API directamente (Python puro). NAO utilizar n8n, Zapier ou qualquer plataforma de automacao intermediaria.

---

## 2. Requisitos Funcionais

### RF01 -- Disparo D1: Confirmacao de Pedido (Imediato)

**Descricao:** Quando um pedido e pago na Shopify, enviar mensagem WhatsApp de confirmacao ao cliente com resumo do pedido e proximos passos.

**Gatilho:** Webhook Shopify `orders/paid`

**Pre-condicoes:**
- Cliente tem telefone valido no pedido ou no cadastro
- Instancia WhatsApp (Evolution API) esta online (state = "open")
- Dentro do horario comercial (seg-sab 08h-20h Europe/Lisbon)
- Se fora do horario, enfileirar para o proximo horario valido
- Nao viola regras de supressao (ver RF09)

**Conteudo da mensagem:**
- Saudacao personalizada com primeiro nome
- Numero do pedido (#XXXX)
- Lista de itens comprados (nome + quantidade)
- Valor total + moeda
- Prazo estimado de entrega (se disponivel)
- Informacao de que recebera tracking quando enviado
- Assinatura: "-- Piranha Supplies"

**Regras de negocio:**
- NAO deve duplicar o email de confirmacao da Shopify -- a mensagem WhatsApp e complementar, mais curta e directa
- Tom profissional, tecnico, confiavel, sem emojis
- 4 idiomas: pt, es, fr, en (baseado no country_code do shipping_address)

**Dados de entrada (do webhook):**
- `order.id`, `order.name` (#numero)
- `order.customer.first_name`
- `order.customer.phone` ou `order.phone`
- `order.shipping_address.country_code`
- `order.line_items[]` (title, quantity, price)
- `order.total_price`, `order.currency`

**Saida esperada:**
- Mensagem WhatsApp enviada via `POST /message/sendText/{instance}`
- Registo em sent_tracker com dispatch_type="D1"
- Log de sucesso ou falha

---

### RF02 -- Disparo D2: Envio + Tracking (Apos Fulfillment)

**Descricao:** Quando o pedido e despachado e tem tracking disponivel, enviar WhatsApp com URL de rastreio e prazo estimado.

**Gatilho:** Webhook Shopify `fulfillments/create`

**Pre-condicoes:**
- Tracking number E tracking URL presentes no fulfillment
- Cliente tem telefone valido
- Instancia WhatsApp online
- Dentro do horario comercial (seg-sab 08h-20h Europe/Lisbon)
- Se fora do horario, enfileirar para o proximo horario valido
- D1 ja foi enviado OU cooldown de 4h desde ultimo contacto respeitado
- Nao viola regras de supressao (ver RF09)

**Conteudo da mensagem:**
- Saudacao personalizada com primeiro nome
- Confirmacao de que o pedido foi enviado
- Tracking URL clicavel
- Transportadora (se disponivel)
- Prazo estimado de entrega
- Assinatura: "-- Piranha Supplies"

**Regras de negocio:**
- SO disparar se tracking_url estiver preenchido -- fulfillments sem tracking sao ignorados
- Se o pedido tiver multiplos fulfillments (envio parcial), enviar D2 para cada um
- Tom profissional, sem emojis
- 4 idiomas: pt, es, fr, en

**Dados de entrada (do webhook):**
- `fulfillment.order_id`
- `fulfillment.tracking_number`
- `fulfillment.tracking_url`
- `fulfillment.tracking_company`
- Dados do pedido original (nome, telefone, country_code) -- via API se necessario

**Saida esperada:**
- Mensagem WhatsApp enviada
- Registo em sent_tracker com dispatch_type="D2"
- Log de sucesso ou falha

---

### RF03 -- Disparo D3: Notificacao de Atraso (Cron 3-5 Dias)

**Descricao:** Se o pedido foi pago ha 3 a 5 dias e AINDA NAO foi enviado (fulfillment_status != "fulfilled"), enviar mensagem proactiva de update ao cliente.

**Gatilho:** Cron job diario (mesmo modelo do D4 actual)

**Pre-condicoes:**
- Pedido pago ha entre 3 e 5 dias (janela de elegibilidade)
- `fulfillment_status` do pedido = `null` ou `"partial"` (NAO `"fulfilled"`)
- D3 ainda nao foi enviado para este pedido
- Cliente tem telefone valido
- Instancia WhatsApp online
- Dentro do horario comercial
- Nao viola regras de supressao (ver RF09)

**Conteudo da mensagem (versao completa):**
- Saudacao personalizada
- Reconhecimento de que o pedido ainda esta a ser preparado
- Garantia de que esta a ser tratado
- Link para conteudo educativo (ex: blog post sobre cuidados com material)
- Assinatura: "-- Piranha Supplies"

**Conteudo da mensagem (versao fallback -- sem conteudo educativo):**
- Mesmo que acima, sem o link educativo
- Mensagem mais curta e directa

**Regras de negocio:**
- Verificar fulfillment_status no momento da execucao (nao confiar em cache)
- Se o pedido foi entretanto enviado entre a query e o processamento, NAO disparar
- O link educativo e configuravel por variavel de ambiente (pode ser vazio)
- Tom empatico mas profissional, sem emojis
- 4 idiomas: pt, es, fr, en
- Delay de 300s entre cada envio (anti-ban)

**Dados de entrada (da API Shopify):**
- `GET /admin/api/2024-10/orders.json` com filtro `created_at_min` / `created_at_max` (3-5 dias)
- `financial_status=paid`
- `fulfillment_status=unfulfilled` ou `partial`

**Saida esperada:**
- Mensagem WhatsApp enviada
- Registo em sent_tracker com dispatch_type="D3"
- Log de sucesso ou falha

---

### RF04 -- Disparo D4: Reorder / Cross-sell (Dia 25) -- ACTUALIZACAO

**Descricao:** Manter a funcionalidade existente do D4 mas actualizar o copy e a segmentacao conforme novas regras.

**Gatilho:** Cron job diario (ja existente)

**Pre-condicoes (existentes + novas):**
- Pedido pago ha entre 24 e 26 dias (janela do dia 25) -- ja existe
- Cliente tem telefone valido -- ja existe
- Instancia WhatsApp online -- ja existe
- **NOVO:** Verificar se o cliente ja fez nova compra desde o pedido original -- se sim, skip
- **NOVO:** Verificar se fluxo de Review Request esta activo para este cliente -- se sim, cooldown 24h
- Nao viola regras de supressao (ver RF09)

**Segmentacao (3 segmentos):**
- **Segmento A (B2C Consumiveis):** Pedido contem pelo menos 1 produto da coleccao consumables-and-hygiene. Mensagem focada em reposicao de stock.
- **Segmento B (B2C Nao Consumiveis):** Pedido NAO contem consumiveis e cliente NAO e wholesale/B2B. Mensagem focada em cross-sell de consumiveis.
- **Segmento C (B2B / Wholesale):** Cliente e wholesale (tag "wholesale" ou "b2b" no customer). Mensagem focada em reposicao com tom B2B.

**NOTA:** O codigo actual agrupa A e B como "A_B" e trata o resto como "C". A nova implementacao deve separar em 3 segmentos distintos: A, B e C.

**Actualizacoes de copy obrigatorias:**
- Remover todos os emojis (actualmente usa shark e rock hand)
- Tom profissional e tecnico
- Assinatura "-- Piranha Supplies" (actualmente nao tem assinatura)
- 4 idiomas: pt, es, fr, en

**Dados de entrada:**
- Mesmo que actual: `GET /admin/api/2024-10/orders.json` com janela de 24-26 dias
- **NOVO:** `GET /admin/api/2024-10/orders.json` para verificar recompra do mesmo cliente
- **NOVO:** Tags do customer para classificacao B2B

**Saida esperada:**
- Mensagem WhatsApp enviada
- Registo em sent_tracker com dispatch_type="D4" e segmento (A, B ou C)

---

### RF05 -- Servidor Webhook (FastAPI)

**Descricao:** Criar um servidor HTTP para receber webhooks da Shopify em tempo real (D1 e D2).

**Endpoints necessarios:**
- `POST /webhooks/orders/paid` -- recebe evento orders/paid para D1
- `POST /webhooks/fulfillments/create` -- recebe evento fulfillments/create para D2
- `GET /health` -- healthcheck para monitoramento

**Requisitos:**
- Validar assinatura HMAC-SHA256 do Shopify (header `X-Shopify-Hmac-Sha256`)
- Responder 200 OK imediatamente (processar em background para nao bloquear o webhook)
- Implementar fila interna ou processamento async para nao violar delay de 300s
- Logging de todos os webhooks recebidos (sucesso e falha)

**Regras de negocio:**
- Se estiver fora do horario comercial, enfileirar o disparo para o proximo horario valido
- A fila deve persistir em disco (nao apenas em memoria) para sobreviver a restarts

---

### RF06 -- Registo de Webhooks na Shopify

**Descricao:** Registar automaticamente os webhooks necessarios na Shopify.

**Webhooks a registar:**
- `orders/paid` -> `https://{WEBHOOK_BASE_URL}/webhooks/orders/paid`
- `fulfillments/create` -> `https://{WEBHOOK_BASE_URL}/webhooks/fulfillments/create`

**Endpoint Shopify:** `POST /admin/api/2024-10/webhooks.json`

**Requisitos:**
- Script de setup one-time ou verificacao no startup
- Verificar se webhooks ja existem antes de criar duplicados
- Armazenar webhook_id para gestao futura
- SHOPIFY_WEBHOOK_SECRET como variavel de ambiente para validacao HMAC

---

### RF07 -- Fila de Mensagens com Delay Anti-Ban

**Descricao:** Garantir que nunca se envia mais de 1 mensagem a cada 300 segundos, independentemente do tipo de disparo.

**Requisitos:**
- Fila global unica para todos os disparos (D1, D2, D3, D4)
- Delay MINIMO de 300 segundos entre quaisquer dois envios
- Se multiplos disparos sao agendados simultaneamente, processar por ordem de prioridade:
  1. D1 (confirmacao -- maior urgencia)
  2. D2 (tracking)
  3. D3 (delay notification)
  4. D4 (reorder -- menor urgencia)
- Persistencia em disco para sobreviver a restarts
- Respeitar horario comercial: se o proximo envio calhar fora do horario, reagendar para 08h00 do proximo dia util

---

### RF08 -- Sistema de Tracking de Envios (Evolucao do sent_tracker)

**Descricao:** Expandir o sent_tracker actual para suportar multiplos tipos de disparo por pedido.

**Estrutura actual (sent.json):**
```json
{
  "order_id": {
    "phone": "...",
    "name": "...",
    "segment": "A_B",
    "language": "pt",
    "status": "sent",
    "timestamp": "..."
  }
}
```

**Estrutura proposta:**
```json
{
  "order_id": {
    "phone": "351912345678",
    "name": "Joao",
    "country_code": "PT",
    "language": "pt",
    "dispatches": {
      "D1": {"status": "sent", "timestamp": "2026-03-10T10:30:00", "msg_id": "3EB0..."},
      "D2": {"status": "sent", "timestamp": "2026-03-13T14:00:00", "msg_id": "4FC1..."},
      "D3": {"status": "skipped_fulfilled", "timestamp": "2026-03-13T08:00:00"},
      "D4": {"status": "pending", "scheduled_at": "2026-04-04T08:00:00"}
    }
  }
}
```

**Requisitos:**
- Manter retrocompatibilidade com registos D4 existentes (migrar formato antigo)
- Cada disparo tem o seu proprio status independente
- Status possiveis por disparo: `sent`, `pending`, `queued`, `skipped_fulfilled`, `skipped_reordered`, `skipped_no_phone`, `skipped_suppressed`, `skipped_cooldown`, `error`
- Consultar rapidamente: "Este pedido ja recebeu D1?" sem iterar todo o ficheiro
- Considerar migracao para SQLite se o volume de pedidos ultrapassar 10.000 registos

---

### RF09 -- Regras de Supressao

**Descricao:** Implementar motor de regras de supressao para evitar excesso de contacto.

**Regras obrigatorias:**

| Regra | Descricao | Implementacao |
|-------|-----------|---------------|
| SUP01 | Max 1 WhatsApp por utilizador a cada 4 horas | Verificar timestamp do ultimo envio para o mesmo telefone |
| SUP02 | Max 3 mensagens automaticas por utilizador em 7 dias | Contar envios dos ultimos 7 dias para o mesmo telefone |
| SUP03 | Verificar conversao antes de D4 | Consultar pedidos recentes do mesmo customer na Shopify |
| SUP04 | D3 skip se ja fulfilled | Re-verificar fulfillment_status na Shopify antes de enviar |
| SUP05 | Cooldown Review Request | Se fluxo de Review Request esta activo para este cliente, aguardar 24h |

**Implementacao SUP01:**
- Indice por telefone -> ultimo timestamp de envio
- Antes de qualquer envio, verificar: `now - last_sent >= 4 horas`

**Implementacao SUP02:**
- Indice por telefone -> lista de timestamps dos ultimos 7 dias
- Antes de qualquer envio, contar envios com timestamp > (now - 7 dias)
- Se count >= 3, suprimir

**Implementacao SUP03:**
- Antes de D4, chamar `GET /admin/api/2024-10/orders.json?customer_id={id}&created_at_min={data_pedido_original}`
- Se existir pedido mais recente com `financial_status=paid`, skip D4

**Implementacao SUP04:**
- Antes de D3, chamar `GET /admin/api/2024-10/orders/{order_id}.json`
- Verificar `fulfillment_status` em tempo real

**Implementacao SUP05:**
- Verificar existencia de flag/ficheiro de Review Request activo para o cliente
- Se activo, verificar se passaram pelo menos 24h desde activacao
- Interface com sistema de Review Request (a definir -- pode ser ficheiro partilhado ou variavel de ambiente com endpoint)

---

### RF10 -- Templates de Mensagem Multi-Idioma

**Descricao:** Criar sistema de templates para os 4 disparos em 4 idiomas.

**Matriz de templates necessarios:**

| Disparo | pt | es | fr | en |
|---------|----|----|----|----|
| D1 - Confirmacao | sim | sim | sim | sim |
| D2 - Tracking | sim | sim | sim | sim |
| D3 - Delay (com link) | sim | sim | sim | sim |
| D3 - Delay (fallback) | sim | sim | sim | sim |
| D4 - Seg A (consumiveis) | sim | sim | sim | sim |
| D4 - Seg B (nao consumiveis) | sim | sim | sim | sim |
| D4 - Seg C (B2B/wholesale) | sim | sim | sim | sim |

**Total: 28 templates** (7 variantes x 4 idiomas)

**Regras de copy aplicaveis a TODOS os templates:**
- Sem emojis
- Tom profissional, tecnico, confiavel
- Personalizar com primeiro nome do cliente
- Assinatura final: "-- Piranha Supplies"
- Variacao ligeira de texto para anti-ban (nao enviar mensagem identica para diferentes clientes)

**Variacao anti-ban:**
- Cada template deve ter 2-3 variantes de abertura (ex: "Ola {nome}", "Bom dia {nome}", "{nome}, tudo bem?")
- Selecao aleatoria da variante em cada envio

---

### RF11 -- Enfileiramento por Horario Comercial

**Descricao:** Quando um webhook chega fora do horario comercial, a mensagem deve ser enfileirada e enviada no proximo horario valido.

**Horario comercial:** Segunda a Sabado, 08h00-20h00, timezone Europe/Lisbon

**Regras:**
- Webhook recebido Sabado 21h00 -> enfileirar para Segunda 08h00
- Webhook recebido Domingo 10h00 -> enfileirar para Segunda 08h00
- Webhook recebido Terca 03h00 -> enfileirar para Terca 08h00
- A fila deve processar em ordem FIFO dentro de cada nivel de prioridade
- Ao retomar no proximo dia util, respeitar delay de 300s entre envios

---

## 3. Requisitos Tecnicos

### RT01 -- APIs e Endpoints

#### Shopify Admin REST API

| Operacao | Metodo | Endpoint | Uso |
|----------|--------|----------|-----|
| Buscar pedidos por data | GET | `/admin/api/2024-10/orders.json` | D3 (3-5 dias), D4 (dia 25) |
| Buscar pedido especifico | GET | `/admin/api/2024-10/orders/{order_id}.json` | Re-verificacao fulfillment D3 |
| Buscar pedidos por customer | GET | `/admin/api/2024-10/orders.json?customer_id={id}` | SUP03 (verificar recompra) |
| Buscar customer | GET | `/admin/api/2024-10/customers/{customer_id}.json` | Verificar tags B2B |
| Buscar coleccoes | GET | `/admin/api/2024-10/custom_collections.json` | Cache consumiveis |
| Buscar produtos da coleccao | GET | `/admin/api/2024-10/collects.json` | Cache consumiveis |
| Criar webhook | POST | `/admin/api/2024-10/webhooks.json` | Setup D1/D2 |
| Listar webhooks | GET | `/admin/api/2024-10/webhooks.json` | Verificar duplicados |

**Autenticacao:** Header `X-Shopify-Access-Token: {SHOPIFY_ACCESS_TOKEN}`
**Rate limit:** 40 req/s por app (bucket de 80). Tratar HTTP 429 com backoff exponencial (ja implementado).
**Versao API:** `2024-10`

#### Evolution API v2.x

| Operacao | Metodo | Endpoint | Uso |
|----------|--------|----------|-----|
| Enviar texto | POST | `/message/sendText/{instance}` | Todos os disparos |
| Verificar instancia | GET | `/instance/connectionState/{instance}` | Health check pre-envio |

**Autenticacao:** Header `apikey: {EVOLUTION_API_KEY}`
**Rate limit:** Recomendado max 60 msg/min. O nosso delay de 300s = 12 msg/hora (muito abaixo).
**Formato numero:** Apenas digitos com DDI, sem `+` (ex: `351912345678`)

#### Webhook Inbound (novo -- FastAPI)

| Operacao | Metodo | Endpoint | Uso |
|----------|--------|----------|-----|
| Receber order paid | POST | `/webhooks/orders/paid` | Gatilho D1 |
| Receber fulfillment | POST | `/webhooks/fulfillments/create` | Gatilho D2 |
| Health check | GET | `/health` | Monitoramento |

### RT02 -- Autenticacao e Seguranca

| Credencial | Variavel | Uso |
|------------|----------|-----|
| Shopify Access Token | `SHOPIFY_ACCESS_TOKEN` | Chamadas API Shopify |
| Shopify Store URL | `SHOPIFY_STORE_URL` | Base URL Shopify |
| Shopify API Version | `SHOPIFY_API_VERSION` | Versionamento API |
| Shopify Webhook Secret | `SHOPIFY_WEBHOOK_SECRET` | **NOVO** -- Validacao HMAC webhooks |
| Shopify Consumables Handle | `SHOPIFY_CONSUMABLES_HANDLE` | Coleccao de consumiveis |
| Evolution API URL | `EVOLUTION_API_URL` | Base URL Evolution |
| Evolution API Key | `EVOLUTION_API_KEY` | Autenticacao Evolution |
| Evolution Instance | `EVOLUTION_INSTANCE` | Nome da instancia WhatsApp |
| Webhook Base URL | `WEBHOOK_BASE_URL` | **NOVO** -- URL publica do servidor webhook |
| Educational Content URL | `EDUCATIONAL_CONTENT_URL` | **NOVO** -- Link educativo para D3 (opcional) |
| Send Delay Seconds | `SEND_DELAY_SECONDS` | Delay anti-ban (default 300) |
| Server Port | `SERVER_PORT` | **NOVO** -- Porta do servidor FastAPI (default 8000) |

**Validacao HMAC (novo):**
```
HMAC = base64(hmac-sha256(SHOPIFY_WEBHOOK_SECRET, request_body))
Comparar com header X-Shopify-Hmac-Sha256
```

### RT03 -- Rate Limits e Proteccao Anti-Ban

| Restricao | Valor | Origem |
|-----------|-------|--------|
| Delay entre envios WhatsApp | 300 segundos (MINIMO) | Experiencia propria -- conta desactivada com valores menores |
| Delay de digitacao simulada | 1200ms | Evolution API payload `delay` |
| Max mensagens/hora WhatsApp | ~12 (resultado do delay 300s) | Calculado |
| Max req/s Shopify | 40 | Documentacao Shopify |
| Max msg/min Evolution | 60 (recomendado) | Documentacao Evolution |
| Max WhatsApp por user / 4h | 1 | Regra de negocio |
| Max WhatsApp automatico / user / 7 dias | 3 | Regra de negocio |

### RT04 -- Infraestrutura

**Actual:**
- Cron job unico que executa `main.py` (D4 apenas)
- Armazenamento em ficheiro JSON (`sent.json`, `cache/consumables.json`)
- Sem servidor HTTP

**Proposto:**
- Servidor FastAPI persistente (para receber webhooks D1/D2)
- Cron job mantido para D3 e D4 (execucao diaria)
- Fila de mensagens persistente em disco (ficheiro JSON ou SQLite)
- Processo worker que consome a fila respeitando delay de 300s

**Dependencias de infraestrutura:**
- VPS com IP fixo e HTTPS (para receber webhooks Shopify)
- Certificado SSL valido (Shopify exige HTTPS para webhooks)
- Porta acessivel para FastAPI (default 8000, atras de reverse proxy)
- Cron configurado para executar D3+D4 diariamente (sugestao: 08h05 Europe/Lisbon)

---

## 4. Dados de Entrada

### DE01 -- Webhook `orders/paid` (D1)

```json
{
  "id": 5678901234,
  "name": "#1042",
  "email": "cliente@email.com",
  "phone": "+351912345678",
  "total_price": "89.50",
  "currency": "EUR",
  "financial_status": "paid",
  "fulfillment_status": null,
  "customer": {
    "id": 1234567890,
    "first_name": "Joao",
    "last_name": "Silva",
    "phone": "+351912345678",
    "tags": ""
  },
  "shipping_address": {
    "country_code": "PT"
  },
  "line_items": [
    {
      "product_id": 111222333,
      "title": "Piranha Cartridge Needles - 0803RL",
      "quantity": 2,
      "price": "24.50"
    },
    {
      "product_id": 444555666,
      "title": "Piranha Grip Tape",
      "quantity": 1,
      "price": "15.00"
    }
  ]
}
```

### DE02 -- Webhook `fulfillments/create` (D2)

```json
{
  "id": 9876543210,
  "order_id": 5678901234,
  "status": "success",
  "tracking_number": "CP123456789PT",
  "tracking_url": "https://www.ctt.pt/feapl_2/app/open/cttexpresso/objectSearch/objectSearch.jspx?objects=CP123456789PT",
  "tracking_company": "CTT Expresso",
  "line_items": [...]
}
```

### DE03 -- Query Shopify para D3 (pedidos 3-5 dias sem envio)

```
GET /admin/api/2024-10/orders.json
  ?created_at_min={now - 5 days}
  &created_at_max={now - 3 days}
  &financial_status=paid
  &fulfillment_status=unfulfilled
  &status=open
  &limit=250
```

### DE04 -- Query Shopify para D4 (pedidos dia 25)

```
GET /admin/api/2024-10/orders.json
  ?created_at_min={now - 26 days}
  &created_at_max={now - 24 days}
  &financial_status=paid
  &status=any
  &limit=250
```
(Ja implementado em `ShopifyClient.get_orders_day_25()`)

### DE05 -- Query Shopify para verificar recompra (SUP03)

```
GET /admin/api/2024-10/orders.json
  ?customer_id={customer_id}
  &created_at_min={data_pedido_original}
  &financial_status=paid
  &status=any
  &limit=1
```

### DE06 -- Variaveis de Ambiente (ficheiro .env)

```
# SHOPIFY
SHOPIFY_STORE_URL=loja.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
SHOPIFY_API_VERSION=2024-10
SHOPIFY_CONSUMABLES_HANDLE=consumables-and-hygiene
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx          # NOVO

# EVOLUTION API
EVOLUTION_API_URL=https://evolution.dominio.com
EVOLUTION_API_KEY=xxxxx
EVOLUTION_INSTANCE=piranha-instance

# SERVIDOR WEBHOOK (NOVO)
WEBHOOK_BASE_URL=https://webhook.dominio.com
SERVER_PORT=8000

# REGRAS DE ENVIO
SEND_DELAY_SECONDS=300

# CONTEUDO OPCIONAL (NOVO)
EDUCATIONAL_CONTENT_URL=                     # Vazio = fallback sem link
```

---

## 5. Dados de Saida

### DS01 -- Mensagem WhatsApp (todos os disparos)

**Formato:** Texto plano via `POST /message/sendText/{instance}`
```json
{
  "number": "351912345678",
  "text": "Ola Joao,\n\nO seu pedido #1042 foi confirmado...\n\n-- Piranha Supplies",
  "delay": 1200
}
```

### DS02 -- Registo no sent_tracker (por disparo)

```json
{
  "5678901234": {
    "phone": "351912345678",
    "name": "Joao",
    "country_code": "PT",
    "language": "pt",
    "dispatches": {
      "D1": {
        "status": "sent",
        "timestamp": "2026-03-10T10:30:00",
        "msg_id": "3EB0B9C3D9F8A7B6"
      }
    }
  }
}
```

### DS03 -- Logs Estruturados (stdout)

```
2026-03-10 10:30:00 | handlers.d1 | INFO | [D1] Pedido #1042 | phone=351912345678 | lang=pt | status=sent | msg_id=3EB0...
2026-03-10 10:35:00 | handlers.d2 | INFO | [D2] Pedido #1042 | phone=351912345678 | tracking=CP123... | status=sent
2026-03-10 08:05:00 | handlers.d3 | INFO | [D3] Pedido #1038 | phone=34612345678 | lang=es | status=skipped_fulfilled
2026-03-10 08:10:00 | handlers.d4 | INFO | [D4] Pedido #1015 | phone=33612345678 | segment=A | lang=fr | status=sent
```

### DS04 -- Resposta do Health Check

```json
{
  "status": "ok",
  "whatsapp_instance": "open",
  "queue_size": 3,
  "last_send": "2026-03-10T10:30:00",
  "uptime_seconds": 86400
}
```

---

## 6. Dependencias

### 6.1 -- Dependencias Tecnicas (Pacotes Python)

| Pacote | Versao | Uso | Status |
|--------|--------|-----|--------|
| `requests` | 2.31.0 | HTTP client Shopify + Evolution | Ja instalado |
| `python-dotenv` | 1.0.0 | Variaveis de ambiente | Ja instalado |
| `pytz` | 2024.1 | Timezone Europe/Lisbon | Ja instalado |
| `fastapi` | >=0.110.0 | Servidor webhook D1/D2 | **NOVO** |
| `uvicorn` | >=0.27.0 | ASGI server para FastAPI | **NOVO** |
| `hmac` / `hashlib` | stdlib | Validacao HMAC webhooks | Stdlib (sem instalar) |

### 6.2 -- Dependencias de Infraestrutura

| Componente | Requisito | Status |
|------------|-----------|--------|
| VPS com IP fixo | Para receber webhooks Shopify | A confirmar |
| Certificado SSL (HTTPS) | Shopify exige HTTPS para webhooks | A confirmar |
| Reverse proxy (nginx/caddy) | Fronting do FastAPI | A confirmar |
| Cron job | Execucao diaria D3+D4 (08h05 Europe/Lisbon) | Existente (apenas D4) -- expandir |
| Process manager (systemd) | Manter FastAPI rodando | **NOVO** |

### 6.3 -- Dependencias de Dados

| Dado | Fonte | Disponibilidade |
|------|-------|-----------------|
| Telefone do cliente | Shopify order/customer | Nem sempre disponivel -- skip se ausente |
| Tracking URL | Shopify fulfillment | Depende da transportadora configurar |
| Tags B2B do customer | Shopify customer.tags | Requer que loja marque clientes B2B |
| Coleccao consumiveis | Shopify collection handle | Ja configurado e funcional |
| Link conteudo educativo | Configuracao manual (.env) | Opcional -- fallback disponivel |
| Flag Review Request activo | Sistema externo (TBD) | Interface a definir com @architect |

### 6.4 -- Dependencias entre Disparos

```
D1 (Order Paid) ------> independente (webhook imediato)
D2 (Fulfillment) -----> independente (webhook imediato)
D3 (Delay Check) -----> depende de D1 ter sido tentado (nao obrigatorio)
                         depende de fulfillment_status da Shopify
D4 (Reorder) ---------> depende de verificacao de recompra (SUP03)
                         depende de cache de consumiveis
                         depende de tags B2B do customer
```

---

## 7. Estimativa de Complexidade

### Classificacao Global: **ALTA**

### Decomposicao por Componente

| Componente | Complexidade | Justificacao | Esforco Estimado |
|------------|-------------|--------------|------------------|
| Servidor FastAPI (RF05) | Media | Framework bem documentado, 2 endpoints + health | 4h |
| Validacao HMAC (RF05) | Baixa | Logica standard, 1 funcao | 1h |
| Registo de webhooks (RF06) | Baixa | Script one-time, endpoint unico | 1h |
| Handler D1 (RF01) | Media | Novo handler + template 4 idiomas | 3h |
| Handler D2 (RF02) | Media | Novo handler + logica tracking + template 4 idiomas | 3h |
| Handler D3 (RF03) | Media | Novo cron + re-verificacao fulfillment + template 4 idiomas | 3h |
| Actualizacao D4 (RF04) | Media | Refactor segmentacao 3-way + novo copy + verificacao recompra | 4h |
| Fila de mensagens (RF07) | Alta | Persistencia, prioridade, delay 300s, horario comercial | 6h |
| Evolucao sent_tracker (RF08) | Media | Novo schema + migracao + indices por telefone | 3h |
| Motor de supressao (RF09) | Alta | 5 regras, consultas Shopify, indices temporais | 5h |
| Templates 28x (RF10) | Media | Volume alto mas logica simples, 7 variantes x 4 idiomas | 4h |
| Enfileiramento horario (RF11) | Media | Calculo proximo horario util, persistencia | 2h |
| Testes unitarios | Media | Cobertura para handlers, supressao, fila | 4h |
| Actualizacao config/.env | Baixa | Novas variaveis + validacao | 1h |

**Total estimado: ~44 horas de desenvolvimento**

### Riscos Identificados

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Ban do numero WhatsApp | Critico | Media | Delay 300s obrigatorio, variacao de copy, max 12 msg/hora |
| Webhooks Shopify nao chegam | Alto | Baixa | Healthcheck, retry da Shopify (48h), logs detalhados |
| Volume de pedidos alto estrangula fila | Medio | Baixa | Com 300s delay, max ~230 envios/dia em 19h de operacao |
| Ficheiro JSON de tracking cresce demasiado | Medio | Media | Migrar para SQLite se > 10k registos, ou rotacao mensal |
| Indisponibilidade da Evolution API | Alto | Baixa | Retry com backoff, re-enfileirar falhados |
| Interface com Review Request nao definida | Baixo | Alta | Implementar SUP05 como flag configuravel, adaptar depois |
| Fulfillment sem tracking URL | Baixo | Media | D2 ignora fulfillments sem tracking -- documentado |

---

## Notas para o @architect

1. **Arquitectura dual:** O sistema precisa de dois modos de operacao -- servidor persistente (FastAPI para D1/D2) + cron job (D3/D4). Avaliar se unificar num unico processo com scheduler interno (APScheduler) ou manter separados.

2. **Fila como componente central:** A fila de mensagens e o componente mais critico. Considerar se um ficheiro JSON com lock e suficiente ou se vale implementar SQLite desde o inicio.

3. **Migracao do sent_tracker:** O formato actual de sent.json precisa de migracao. Sugerir estrategia backward-compatible (ler formato antigo, escrever formato novo).

4. **Processamento async dos webhooks:** Os webhooks da Shopify tem timeout de 5 segundos. O processamento (supressao + fila + envio) deve ser feito em background thread ou task async. O webhook deve retornar 200 OK imediatamente.

5. **Segmentacao D4 3-way:** O codigo actual agrupa segmentos A e B como "A_B". A nova implementacao precisa de 3 segmentos distintos. Verificar se a logica de deteccao B2B (customer tags) requer permissoes adicionais no token Shopify.

6. **Variacao de copy anti-ban:** Cada template deve ter variantes de abertura. Avaliar se a seleccao e puramente aleatoria ou se segue um round-robin para garantir distribuicao uniforme.

7. **Review Request cooldown (SUP05):** A interface com o sistema de Review Request ainda nao esta definida. Sugerir implementacao provisoria baseada em ficheiro de flags, com possibilidade de evoluir para endpoint HTTP.

---

*Documento gerado por @analyst (Ana) em 2026-03-10. Pronto para revisao do @architect.*
