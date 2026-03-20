# Pesquisa: Post Purchase WhatsApp -- 4 Disparos

**Projecto:** `post-purchase-wpp`
**Agente:** @researcher (Rex)
**Data:** 2026-03-10
**Versao:** 1.0
**Status:** Pronto para @mapper e @dev
**Base:** Documentos `01-analyst-requirements.md` e `02-architect-blueprint.md`

---

## Servicos Identificados

1. **Shopify Admin REST API** -- gestao de pedidos, customers, fulfillments, webhooks, coleccoes
2. **Evolution API v2.x** -- envio de mensagens WhatsApp e verificacao de instancia
3. **Webhook Inbound Server (Flask)** -- servidor proprio para receber webhooks da Shopify (a desenvolver)

---

## 1. Shopify Admin REST API

**Base URL:**
```
https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}/
```
Exemplo concreto: `https://piranhasupplies.myshopify.com/admin/api/2024-10/`

**Autenticacao:**
```
X-Shopify-Access-Token: {SHOPIFY_ACCESS_TOKEN}
Content-Type: application/json
```

**Rate Limit:**
- 40 requisicoes/segundo por app (por loja)
- Bucket size: 80 requests
- Header de controlo: `X-Shopify-Shop-Api-Call-Limit: 32/40`
- Resposta em excesso: HTTP 429 (tratar com backoff exponencial -- ja implementado no projecto)

**Versao API:** `2024-10`

**Paginacao:**
- Maximo 250 itens por pagina
- Cursor-based: usar `Link` header para navegar paginas
- Parametro `limit` aceita 1-250

---

### 1.1 GET /admin/api/2024-10/orders.json

**Uso neste projecto:** D3 (pedidos 3-5 dias sem envio), D4 (pedidos dia 25), SUP03 (verificar recompra)

| Parametro | Tipo | Descricao | Obrigatorio |
|-----------|------|-----------|-------------|
| `status` | string | `open`, `closed`, `cancelled`, `any` | Nao (default: `open`) |
| `financial_status` | string | `paid`, `pending`, `refunded`, `partially_paid` | Nao |
| `fulfillment_status` | string | `fulfilled`, `unfulfilled`, `partial` | Nao |
| `created_at_min` | datetime | Pedidos apos esta data (ISO 8601) | Nao |
| `created_at_max` | datetime | Pedidos antes desta data (ISO 8601) | Nao |
| `customer_id` | integer | Filtrar por customer ID | Nao |
| `limit` | integer | Maximo 250 | Nao (default: 50) |

#### Request D3 -- Pedidos 3-5 dias sem envio

```
GET /admin/api/2024-10/orders.json?created_at_min={now-5d}&created_at_max={now-3d}&financial_status=paid&fulfillment_status=unfulfilled&status=open&limit=250
```

**Nota:** E necessario fazer uma segunda request com `fulfillment_status=partial` para capturar envios parciais. A API da Shopify nao suporta multiplos valores no parametro `fulfillment_status`.

```python
# Request 1: unfulfilled
params_unfulfilled = {
    "created_at_min": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "created_at_max": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "financial_status": "paid",
    "fulfillment_status": "unfulfilled",
    "status": "open",
    "limit": 250,
}

# Request 2: partial
params_partial = {
    "created_at_min": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "created_at_max": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "financial_status": "paid",
    "fulfillment_status": "partial",
    "status": "open",
    "limit": 250,
}
```

#### Request D4 -- Pedidos dia 25

```
GET /admin/api/2024-10/orders.json?created_at_min={now-26d}&created_at_max={now-24d}&financial_status=paid&status=any&limit=250
```

```python
params_d4 = {
    "created_at_min": (now - timedelta(days=26)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "created_at_max": (now - timedelta(days=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "financial_status": "paid",
    "status": "any",
    "limit": 250,
}
```

#### Request SUP03 -- Verificar recompra

```
GET /admin/api/2024-10/orders.json?customer_id={customer_id}&created_at_min={data_pedido_original}&financial_status=paid&status=any&limit=2
```

```python
params_reorder = {
    "customer_id": customer_id,
    "created_at_min": order_created_at,  # ISO 8601
    "financial_status": "paid",
    "status": "any",
    "limit": 2,  # 2 porque o primeiro pode ser o proprio pedido original
}
# Se len(orders) > 1 -> cliente fez recompra
```

#### Exemplo de Response (orders.json)

```json
{
  "orders": [
    {
      "id": 5678901234,
      "name": "#1042",
      "email": "cliente@email.com",
      "phone": "+351912345678",
      "total_price": "89.50",
      "currency": "EUR",
      "financial_status": "paid",
      "fulfillment_status": null,
      "created_at": "2026-03-10T10:30:00+00:00",
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
  ]
}
```

#### Campos Criticos para o Projecto

- `order.id` (integer) -- identificador unico do pedido, usado como chave no sent_tracker
- `order.name` (string, ex: "#1042") -- numero legivel do pedido para templates de mensagem
- `order.phone` (string, formato E.164 com "+") -- telefone de contacto (pode ser `null`)
- `order.customer.id` (integer) -- ID do customer para verificar recompra (SUP03) e tags B2B
- `order.customer.first_name` (string) -- para personalizacao de mensagem
- `order.customer.phone` (string, formato E.164) -- fallback se `order.phone` nao existir
- `order.customer.tags` (string) -- tags separadas por virgula, verificar "wholesale" ou "b2b" para D4 segmento C
- `order.shipping_address.country_code` (string, ISO 3166-1 alpha-2, ex: "PT") -- para determinar idioma da mensagem
- `order.financial_status` (string) -- deve ser "paid" para todos os disparos
- `order.fulfillment_status` (string | null) -- `null` = unfulfilled, `"partial"`, `"fulfilled"` -- critico para D3
- `order.line_items[].product_id` (integer) -- para cruzar com lista de consumiveis (D4 segmento A)
- `order.line_items[].title` (string) -- nome do produto para template D1
- `order.line_items[].quantity` (integer) -- quantidade para template D1
- `order.line_items[].price` (string) -- preco unitario como string decimal
- `order.total_price` (string) -- total como string decimal (ex: "89.50")
- `order.currency` (string, ISO 4217, ex: "EUR") -- moeda para template D1
- `order.created_at` (string, ISO 8601) -- data de criacao para calcular janelas temporais (D3: 3-5 dias, D4: dia 25)

#### Erros Comuns

- `HTTP 429` -- rate limit excedido. Respeitar header `Retry-After`. Implementar backoff exponencial (ja existente no projecto).
- `HTTP 401` -- token invalido ou expirado. Verificar `SHOPIFY_ACCESS_TOKEN`.
- `HTTP 404` -- pedido/customer nao encontrado. Pode acontecer se o pedido foi eliminado.

---

### 1.2 GET /admin/api/2024-10/orders/{order_id}.json

**Uso neste projecto:** Re-verificacao de `fulfillment_status` em tempo real para D3 (SUP04), buscar dados do pedido para D2 quando `needs_order_fetch=true`.

#### Parametros de Request

Nenhum parametro de query necessario -- apenas o `order_id` no path.

```python
url = f"https://{STORE_URL}/admin/api/2024-10/orders/{order_id}.json"
response = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN})
order = response.json().get("order", {})
```

#### Exemplo de Response

```json
{
  "order": {
    "id": 5678901234,
    "name": "#1042",
    "phone": "+351912345678",
    "fulfillment_status": null,
    "financial_status": "paid",
    "customer": {
      "id": 1234567890,
      "first_name": "Joao",
      "phone": "+351912345678"
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
      }
    ],
    "total_price": "89.50",
    "currency": "EUR",
    "created_at": "2026-03-10T10:30:00+00:00"
  }
}
```

#### Campos Criticos para o Projecto

- `order.fulfillment_status` -- verificar em tempo real antes de enviar D3. Se `"fulfilled"`, skip e marcar `skipped_fulfilled`.
- Todos os campos de contacto (`phone`, `customer.first_name`, `shipping_address.country_code`) -- para preencher dados quando D2 chega via webhook sem informacao do cliente.

---

### 1.3 GET /admin/api/2024-10/customers/{customer_id}.json

**Uso neste projecto:** Verificar tags B2B do customer para classificacao de segmento D4 (segmento C: "wholesale" ou "b2b").

#### Parametros de Request

Nenhum parametro de query -- apenas `customer_id` no path.

```python
url = f"https://{STORE_URL}/admin/api/2024-10/customers/{customer_id}.json"
response = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN})
customer = response.json().get("customer", {})
```

#### Exemplo de Response

```json
{
  "customer": {
    "id": 1234567890,
    "first_name": "Joao",
    "last_name": "Silva",
    "email": "joao@email.com",
    "phone": "+351912345678",
    "orders_count": 5,
    "total_spent": "450.00",
    "tags": "wholesale, premium",
    "note": ""
  }
}
```

#### Campos Criticos para o Projecto

- `customer.tags` (string) -- tags separadas por virgula. Para D4 segmento C, verificar se contem "wholesale" ou "b2b" (case-insensitive, com trim):
  ```python
  tags = (customer.get("tags", "") or "").lower().split(",")
  tags = [t.strip() for t in tags]
  is_b2b = "wholesale" in tags or "b2b" in tags
  ```
- `customer.id` (integer) -- para consultas subsequentes
- `customer.first_name` (string) -- fallback para nome do cliente
- `customer.phone` (string) -- fallback para telefone

---

### 1.4 GET /admin/api/2024-10/custom_collections.json

**Uso neste projecto:** Cache de IDs de produtos consumiveis para D4 segmento A. Ja implementado no projecto actual.

```python
url = f"https://{STORE_URL}/admin/api/2024-10/custom_collections.json"
params = {"handle": "consumables-and-hygiene"}
response = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN}, params=params)
collections = response.json().get("custom_collections", [])
collection_id = collections[0]["id"] if collections else None
```

#### Exemplo de Response

```json
{
  "custom_collections": [
    {
      "id": 789012345,
      "handle": "consumables-and-hygiene",
      "title": "Consumables & Hygiene"
    }
  ]
}
```

#### Campos Criticos

- `custom_collections[0].id` (integer) -- necessario para buscar produtos da coleccao via `collects.json`

---

### 1.5 GET /admin/api/2024-10/collects.json

**Uso neste projecto:** Buscar `product_id` dos produtos na coleccao de consumiveis. Ja implementado.

```python
url = f"https://{STORE_URL}/admin/api/2024-10/collects.json"
params = {"collection_id": collection_id, "limit": 250}
response = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN}, params=params)
collects = response.json().get("collects", [])
consumable_product_ids = {c["product_id"] for c in collects}
```

#### Exemplo de Response

```json
{
  "collects": [
    {
      "id": 111,
      "collection_id": 789012345,
      "product_id": 111222333,
      "position": 1
    },
    {
      "id": 112,
      "collection_id": 789012345,
      "product_id": 222333444,
      "position": 2
    }
  ]
}
```

#### Campos Criticos

- `collects[].product_id` (integer) -- cruzar com `order.line_items[].product_id` para determinar se pedido contem consumiveis (D4 segmento A)

---

### 1.6 POST /admin/api/2024-10/webhooks.json

**Uso neste projecto:** Registar webhooks `orders/paid` e `fulfillments/create` na Shopify (setup one-time).

#### Parametros de Request

```json
{
  "webhook": {
    "topic": "orders/paid",
    "address": "https://{WEBHOOK_BASE_URL}/webhooks/orders/paid",
    "format": "json"
  }
}
```

| Campo | Tipo | Descricao | Obrigatorio |
|-------|------|-----------|-------------|
| `topic` | string | Evento a subscrever | Sim |
| `address` | string | URL HTTPS de destino | Sim |
| `format` | string | `"json"` ou `"xml"` | Sim |

**Topics necessarios:**
- `orders/paid` -- gatilho para D1 (confirmacao de pedido)
- `fulfillments/create` -- gatilho para D2 (envio + tracking)

#### Exemplo de Response

```json
{
  "webhook": {
    "id": 901234567,
    "topic": "orders/paid",
    "address": "https://webhook.dominio.com/webhooks/orders/paid",
    "format": "json",
    "created_at": "2026-03-10T10:00:00+00:00"
  }
}
```

#### Campos Criticos

- `webhook.id` (integer) -- armazenar para gestao futura (desactivar, actualizar)

#### Requisitos de Seguranca

- **HTTPS obrigatorio** -- a Shopify recusa URLs HTTP para webhooks
- **Validacao HMAC** -- a Shopify envia header `X-Shopify-Hmac-Sha256` com cada webhook:
  ```python
  import hmac
  import hashlib
  import base64

  def validate_hmac(raw_body: bytes, hmac_header: str, secret: str) -> bool:
      computed = base64.b64encode(
          hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
      ).decode("utf-8")
      return hmac.compare_digest(computed, hmac_header)
  ```
- **Timeout:** Shopify espera resposta em 5 segundos. Se nao receber, marca como falhado e re-tenta.

---

### 1.7 GET /admin/api/2024-10/webhooks.json

**Uso neste projecto:** Verificar webhooks existentes antes de registar novos (evitar duplicados).

```python
url = f"https://{STORE_URL}/admin/api/2024-10/webhooks.json"
response = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN})
webhooks = response.json().get("webhooks", [])
existing_topics = {w["topic"]: w["id"] for w in webhooks}
```

#### Exemplo de Response

```json
{
  "webhooks": [
    {
      "id": 901234567,
      "topic": "orders/paid",
      "address": "https://webhook.dominio.com/webhooks/orders/paid",
      "format": "json"
    }
  ]
}
```

---

### 1.8 Payload do Webhook `orders/paid` (Recebido pelo nosso servidor)

**Nota:** Este e o body que a Shopify envia ao nosso endpoint `POST /webhooks/orders/paid`. Nao e um endpoint que chamamos -- e o que recebemos.

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
  "created_at": "2026-03-10T10:30:00+00:00",
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

**Headers da Shopify enviados com o webhook:**
- `X-Shopify-Hmac-Sha256` -- assinatura HMAC para validacao (base64-encoded)
- `X-Shopify-Topic` -- ex: `orders/paid`
- `X-Shopify-Shop-Domain` -- dominio da loja
- `X-Shopify-Webhook-Id` -- ID unico do envio

**Campos a extrair para o item de fila D1:**
- `id` -> `order_id` (converter para string)
- `name` -> `order_name`
- `customer.first_name` -> `customer_name` (fallback: `"cliente"`)
- `phone` OU `customer.phone` -> `phone` (prioridade: `order.phone` > `customer.phone`)
- `shipping_address.country_code` -> `country_code`
- `line_items` -> `data.line_items`
- `total_price` -> `data.total_price`
- `currency` -> `data.currency`
- `customer.id` -> `customer_id` (converter para string)

---

### 1.9 Payload do Webhook `fulfillments/create` (Recebido pelo nosso servidor)

```json
{
  "id": 9876543210,
  "order_id": 5678901234,
  "status": "success",
  "tracking_number": "CP123456789PT",
  "tracking_url": "https://www.ctt.pt/feapl_2/app/open/cttexpresso/objectSearch/objectSearch.jspx?objects=CP123456789PT",
  "tracking_company": "CTT Expresso",
  "line_items": [
    {
      "product_id": 111222333,
      "title": "Piranha Cartridge Needles - 0803RL",
      "quantity": 2,
      "price": "24.50"
    }
  ]
}
```

**Campos a extrair para o item de fila D2:**
- `order_id` -> `order_id` (converter para string)
- `tracking_number` -> `data.tracking_number`
- `tracking_url` -> `data.tracking_url` -- **SO ENFILEIRAR SE PRESENTE E NAO VAZIO**
- `tracking_company` -> `data.tracking_company`

**ATENCAO:** O payload de `fulfillments/create` NAO inclui dados do cliente (nome, telefone, country_code). Para obter esses dados:
1. Primeiro, verificar se o `order_id` ja existe no `sent_tracker` (pode ter dados do D1)
2. Se nao existir, marcar `needs_order_fetch=true` no item de fila
3. O worker ira chamar `GET /admin/api/2024-10/orders/{order_id}.json` para obter os dados em falta

---

### 1.10 Politica de Retry dos Webhooks Shopify

**Documentado na knowledge base:** A Shopify envia o header `X-Shopify-Hmac-Sha256` para validacao.

**Informacao complementar (lacuna parcial -- ver seccao de lacunas):**
- A Shopify re-tenta webhooks falhados durante 48 horas
- Se o endpoint retornar um codigo HTTP nao-2xx, a Shopify reagenda o envio
- Apos falhas consecutivas durante 48h, o webhook pode ser desactivado automaticamente pela Shopify
- O nosso servidor DEVE responder HTTP 200 em menos de 5 segundos

---

## 2. Evolution API v2.x

**Base URL:**
```
{EVOLUTION_API_URL}
```
Exemplo: `https://evolution.dominio.com`

**Autenticacao:**
```
apikey: {EVOLUTION_API_KEY}
Content-Type: application/json
```

**Rate Limit:**
- Sem limite hard documentado na API
- Recomendado: max 60 mensagens/minuto por instancia
- **Regra do projecto (OBRIGATORIA):** delay de 300 segundos entre envios = ~12 mensagens/hora. Valor determinado por experiencia propria (conta foi banida com valores menores).

**Versao:** Evolution API v2.x (baseada em Baileys/WhatsApp Web)

---

### 2.1 POST /message/sendText/{instance}

**Uso neste projecto:** Envio de TODAS as mensagens WhatsApp (D1, D2, D3, D4). Este e o UNICO endpoint de envio utilizado -- apenas texto, sem media.

#### Parametros de Request

```json
{
  "number": "351912345678",
  "text": "Ola Joao,\n\nO seu pedido #1042 foi confirmado...\n\n-- Piranha Supplies",
  "delay": 1200
}
```

| Campo | Tipo | Descricao | Obrigatorio |
|-------|------|-----------|-------------|
| `number` | string | Numero com DDI, SEM "+" (ex: `"351912345678"`) | Sim |
| `text` | string | Texto da mensagem (suporta `\n` para quebras de linha) | Sim |
| `delay` | integer | Delay em milissegundos que simula digitacao humana | Nao (recomendado: `1200`) |

**FORMATO DO NUMERO -- CRITICO:**
- CORRECTO: `"351912345678"` (DDI + numero, apenas digitos)
- INCORRECTO: `"+351912345678"` (com +)
- INCORRECTO: `"912345678"` (sem DDI)
- INCORRECTO: `"(351) 912-345-678"` (com formatacao)

**Normalizacao obrigatoria antes do envio:**
```python
def normalize_phone(raw_phone: str) -> str:
    """Remove tudo que nao e digito. Remove '+' do inicio."""
    digits = ''.join(c for c in raw_phone if c.isdigit())
    return digits  # Ex: "+351912345678" -> "351912345678"
```

#### Exemplo de Response (Sucesso)

```json
{
  "key": {
    "remoteJid": "351912345678@s.whatsapp.net",
    "fromMe": true,
    "id": "3EB0B9C3D9F8A7B6"
  },
  "message": {
    "conversation": "Ola Joao,\n\nO seu pedido #1042 foi confirmado..."
  },
  "status": "PENDING"
}
```

#### Campos Criticos para o Projecto

- `key.id` (string) -- ID unico da mensagem enviada. Registar no `sent_tracker` como `msg_id` para rastreabilidade.
- `status` (string) -- `"PENDING"` significa que a mensagem foi aceite pela API e esta a ser enviada. NAO significa que foi entregue ao destinatario.

#### Erros Comuns

- `HTTP 400` -- payload invalido (numero mal formatado, texto vazio)
- `HTTP 401` -- apikey invalida
- `HTTP 404` -- instancia nao encontrada ou nao existe
- `HTTP 500` -- erro interno na Evolution API (instancia pode estar desconectada)
- Numero nao registado no WhatsApp -- a API pode retornar sucesso mas a mensagem nao sera entregue. Nao ha como validar previamente via API.

---

### 2.2 GET /instance/connectionState/{instance}

**Uso neste projecto:** Verificacao pre-envio da instancia WhatsApp. Executada pelo worker antes de cada envio e pelo health check.

#### Parametros de Request

Nenhum parametro de query -- apenas o nome da instancia no path.

```python
url = f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE}"
headers = {"apikey": EVOLUTION_API_KEY}
response = requests.get(url, headers=headers)
data = response.json()
state = data.get("instance", {}).get("state", "unknown")
```

#### Exemplo de Response

```json
{
  "instance": {
    "instanceName": "piranha-instance",
    "state": "open"
  }
}
```

#### Estados Possiveis

| Estado | Descricao | Accao no Projecto |
|--------|-----------|-------------------|
| `"open"` | Conectado ao WhatsApp | Prosseguir com envio |
| `"connecting"` | A conectar (aguardando QR Code) | Aguardar, re-tentar em 60s |
| `"close"` | Desconectado | Aguardar, re-tentar em 60s, log warning |

#### Campos Criticos

- `instance.state` (string) -- DEVE ser `"open"` para permitir envio. Qualquer outro estado = nao enviar, item permanece na fila.

#### Erros Comuns

- `HTTP 404` -- instancia nao existe. Verificar `EVOLUTION_INSTANCE` no .env.
- `HTTP 401` -- apikey invalida.

---

## 3. Webhook Inbound Server (Flask) -- A Desenvolver

**Nota:** Este nao e uma API externa -- e o servidor que o projecto ira implementar para receber webhooks da Shopify.

**Base URL (publica):**
```
https://{WEBHOOK_BASE_URL}
```
Porta interna: `{SERVER_PORT}` (default 8000), por tras de reverse proxy nginx com SSL.

**Framework:** Flask 3.0.3 (decisao arquitectural DA01 -- manter consistencia com `piranha-supplies-voice`)

### Endpoints a Implementar

| Endpoint | Metodo | Descricao | Resposta |
|----------|--------|-----------|----------|
| `/webhooks/orders/paid` | POST | Recebe webhook `orders/paid` da Shopify, valida HMAC, enfileira D1 | 200 OK |
| `/webhooks/fulfillments/create` | POST | Recebe webhook `fulfillments/create`, valida HMAC, enfileira D2 | 200 OK |
| `/health` | GET | Health check com estado da instancia WhatsApp e tamanho da fila | 200 JSON |

### Validacao HMAC (em cada webhook recebido)

```python
import hmac
import hashlib
import base64

def validate_hmac(raw_body: bytes, hmac_header: str) -> bool:
    """
    Valida assinatura HMAC-SHA256 do webhook Shopify.

    IMPORTANTE: No Flask, ler request.get_data() ANTES de request.get_json()
    porque get_json() consome o stream. Guardar raw body primeiro.

    Args:
        raw_body: request.get_data() -- bytes do corpo do request
        hmac_header: request.headers.get("X-Shopify-Hmac-Sha256")
    Returns:
        True se assinatura valida
    """
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "").encode("utf-8")
    computed = base64.b64encode(
        hmac.new(secret, raw_body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)
```

**ATENCAO FLASK:** A ordem de leitura do request body e critica:
```python
@app.route("/webhooks/orders/paid", methods=["POST"])
def handle_order_paid():
    raw_body = request.get_data()  # 1. LER RAW PRIMEIRO
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not validate_hmac(raw_body, hmac_header):
        return "Unauthorized", 401

    data = json.loads(raw_body)  # 2. PARSE DEPOIS (nao usar request.get_json())
    # ... processar ...
    return "OK", 200
```

### Formato de Resposta do Health Check

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

## 4. Regras de Negocio Relevantes (da Knowledge Base)

### 4.1 Horario Comercial

| Canal | Horario | Dias |
|-------|---------|------|
| WhatsApp | 08h00 - 20h00 | Segunda a Sabado |

- **Timezone:** Europe/Lisbon
- Domingos: NAO enviar (enfileirar para Segunda 08h00)
- Sabado apos 20h00: enfileirar para Segunda 08h00
- Dia util antes das 08h00: enfileirar para mesmo dia 08h00

### 4.2 Tom de Voz (Regras de Mensagem)

- Profissional, tecnico, confiavel
- Personalizado com primeiro nome
- **SEM emojis** (regra explicita para este projecto)
- Assinatura final: `"\n\n-- Piranha Supplies"` (duas quebras de linha antes)
- 4 idiomas: pt, es, fr, en (baseado em `shipping_address.country_code`)

### 4.3 Anti-Ban

| Restricao | Valor | Origem |
|-----------|-------|--------|
| Delay entre envios | 300 segundos (MINIMO) | Experiencia propria |
| Delay de digitacao | 1200ms (`delay` no payload) | Evolution API |
| Max mensagens/hora | ~12 (resultado do delay 300s) | Calculado |
| Variacao de abertura | 3 variantes por template | Anti-ban |

### 4.4 Regras de Supressao

| Regra | Descricao | Implementacao |
|-------|-----------|---------------|
| SUP01 | Max 1 WhatsApp por telefone a cada 4h | `sent_tracker.get_last_send_timestamp(phone)` |
| SUP02 | Max 3 mensagens automaticas por telefone em 7 dias | `sent_tracker.count_sends_last_7_days(phone)` |
| SUP03 | Verificar recompra antes de D4 | `shopify.check_reorder(customer_id, since_date)` |
| SUP04 | D3 skip se fulfillment confirmado | `shopify.get_order(order_id)` -> verificar `fulfillment_status` |
| SUP05 | Cooldown de 24h se Review Request activo | Ficheiro `review_requests.json` (interface provisoria) |

### 4.5 Mapeamento Pais -> Idioma

Baseado no `shipping_address.country_code`:

| Pais/Regiao | `country_code` | Idioma |
|-------------|----------------|--------|
| Portugal | PT | pt |
| Brasil | BR | pt |
| Espanha | ES | es |
| Mexico, Colombia, Argentina, etc. | MX, CO, AR, etc. | es |
| Franca | FR | fr |
| Belgica (FR) | BE | fr |
| Canada (FR) | CA | fr |
| UK, EUA, Irlanda, etc. | GB, US, IE, etc. | en |
| Todos os outros | * | en (fallback) |

**Nota:** O `language_detector.py` ja existe no projecto. Verificar se cobre todos os paises de destino da loja.

### 4.6 Formato do Numero de Telefone

**Entrada (Shopify):** formato E.164 com "+" (ex: `"+351912345678"`)
**Saida (Evolution API):** apenas digitos sem "+" (ex: `"351912345678"`)

O `phone_normalizer.py` ja existe no projecto e faz esta conversao.

**Prioridade de telefone:**
1. `order.phone` (telefone do pedido)
2. `order.customer.phone` (telefone do cadastro do cliente)
3. Se ambos `null` ou vazios -> skip envio, marcar `skipped_no_phone`

---

## 5. Infraestrutura (da Knowledge Base)

### 5.1 VPS

- **Estrutura de pastas:** `/home/ubuntu/projetos/post-purchase-wpp/`
- **Process manager:** systemd para processos continuos (webhook server + worker)
- **Cron:** crontab para D3+D4 dispatcher (diario as 08h05 seg-sab)
- **Reverse proxy:** nginx com SSL (Let's Encrypt) para HTTPS

### 5.2 Padrao Python

- **Logging:**
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
  )
  ```
- **Retry com backoff:** decorator `@retry(max_attempts=3, delay=2, backoff=2)` (ja implementado)
- **Variaveis de ambiente:** `python-dotenv` com `load_dotenv()`

### 5.3 Crontab para D3+D4

```bash
# Seg-Sab as 08h05 Europe/Lisbon
5 8 * * 1-6 cd /home/ubuntu/projetos/post-purchase-wpp && /home/ubuntu/projetos/post-purchase-wpp/venv/bin/python -m src.cron_dispatcher >> /var/log/piranha-wpp-cron.log 2>&1
```

### 5.4 File Locking (fcntl)

Para concorrencia entre webhook server e worker no acesso a `queue.json` e `sent.json`:

```python
import fcntl
import json

def safe_read_write(filepath, operation_fn):
    """Padrao de leitura/escrita com file lock."""
    with open(filepath, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Lock exclusivo
        data = json.load(f)
        result = operation_fn(data)
        f.seek(0)
        f.truncate()
        json.dump(data, f, indent=2)
        # Lock libertado automaticamente no close
    return result
```

**Nota:** `fcntl.flock` funciona em Linux (VPS Ubuntu) e macOS. Usar com timeout de 10 segundos para evitar deadlocks:
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("File lock timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 segundos timeout
try:
    fcntl.flock(f, fcntl.LOCK_EX)
finally:
    signal.alarm(0)  # Cancelar alarme
```

---

## 6. Variaveis de Ambiente Completas

```bash
# -- SHOPIFY --
SHOPIFY_STORE_URL=piranhasupplies.myshopify.com     # Dominio Shopify (sem https://)
SHOPIFY_ACCESS_TOKEN=shpat_xxxxx                      # Token de acesso Admin API
SHOPIFY_API_VERSION=2024-10                            # Versao da API
SHOPIFY_CONSUMABLES_HANDLE=consumables-and-hygiene     # Handle da coleccao consumiveis
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx                     # NOVO -- Secret para HMAC webhooks

# -- EVOLUTION API --
EVOLUTION_API_URL=https://evolution.dominio.com        # URL base da Evolution API
EVOLUTION_API_KEY=xxxxx                                 # API key
EVOLUTION_INSTANCE=piranha-instance                     # Nome da instancia WhatsApp

# -- SERVIDOR WEBHOOK (NOVO) --
WEBHOOK_BASE_URL=https://webhook.dominio.com           # URL publica (HTTPS obrigatorio)
SERVER_PORT=8000                                        # Porta Flask (atras de nginx)

# -- REGRAS DE ENVIO --
SEND_DELAY_SECONDS=300                                  # NAO ALTERAR

# -- CONTEUDO OPCIONAL (NOVO) --
EDUCATIONAL_CONTENT_URL=                                # URL conteudo educativo D3 (vazio = fallback)
REVIEW_REQUEST_FILE=                                    # Path ficheiro review requests (vazio = skip SUP05)
```

---

## 7. Resumo de Endpoints por Disparo

### D1 -- Confirmacao de Pedido

| Etapa | Endpoint | Metodo | Quem Chama |
|-------|----------|--------|------------|
| Gatilho | `/webhooks/orders/paid` (nosso server) | POST (recebido) | Shopify |
| Envio | `/message/sendText/{instance}` | POST | Worker |
| Health | `/instance/connectionState/{instance}` | GET | Worker |

### D2 -- Envio + Tracking

| Etapa | Endpoint | Metodo | Quem Chama |
|-------|----------|--------|------------|
| Gatilho | `/webhooks/fulfillments/create` (nosso server) | POST (recebido) | Shopify |
| Dados pedido (se necessario) | `/admin/api/2024-10/orders/{order_id}.json` | GET | Worker |
| Envio | `/message/sendText/{instance}` | POST | Worker |
| Health | `/instance/connectionState/{instance}` | GET | Worker |

### D3 -- Notificacao de Atraso

| Etapa | Endpoint | Metodo | Quem Chama |
|-------|----------|--------|------------|
| Busca pedidos | `/admin/api/2024-10/orders.json` (unfulfilled 3-5d) | GET | Cron Dispatcher |
| Re-verificacao | `/admin/api/2024-10/orders/{order_id}.json` | GET | Cron Dispatcher |
| Envio | `/message/sendText/{instance}` | POST | Worker |
| Health | `/instance/connectionState/{instance}` | GET | Worker |

### D4 -- Reorder / Cross-sell

| Etapa | Endpoint | Metodo | Quem Chama |
|-------|----------|--------|------------|
| Busca pedidos dia 25 | `/admin/api/2024-10/orders.json` (24-26d) | GET | Cron Dispatcher |
| Verificar recompra | `/admin/api/2024-10/orders.json` (customer_id) | GET | Cron Dispatcher |
| Buscar tags B2B | `/admin/api/2024-10/customers/{customer_id}.json` | GET | Cron Dispatcher |
| Cache consumiveis | `/admin/api/2024-10/custom_collections.json` + `/collects.json` | GET | Cron Dispatcher |
| Envio | `/message/sendText/{instance}` | POST | Worker |
| Health | `/instance/connectionState/{instance}` | GET | Worker |

### Setup (one-time)

| Etapa | Endpoint | Metodo | Quem Chama |
|-------|----------|--------|------------|
| Listar webhooks | `/admin/api/2024-10/webhooks.json` | GET | register_webhooks.py |
| Criar webhook | `/admin/api/2024-10/webhooks.json` | POST | register_webhooks.py |

---

## 8. Lacunas Identificadas

### LAC01 -- Schema exacto do payload `fulfillments/create` (PARCIAL)

**Situacao:** A knowledge base em `knowledge/apis/shopify/webhooks.md` documenta como criar webhooks mas NAO documenta o schema completo do payload recebido para `fulfillments/create`. O exemplo de payload no documento `01-analyst-requirements.md` (DE02) foi usado como referencia, mas pode faltar campos opcionais.

**Campos confirmados pelo analyst:**
- `id`, `order_id`, `status`, `tracking_number`, `tracking_url`, `tracking_company`, `line_items`

**Campos potencialmente em falta (nao documentados):**
- `tracking_numbers` (array, quando multiplos tracking)
- `tracking_urls` (array)
- `destination` (informacao de destino)
- `shipment_status` (status de entrega)

**Recomendacao:** O @dev deve logar o payload completo do primeiro webhook recebido para confirmar o schema. A implementacao deve ser defensiva com `.get()` e defaults para todos os campos.

**Impacto:** Baixo. Os campos essenciais (`tracking_url`, `tracking_number`, `tracking_company`, `order_id`) estao confirmados.

---

### LAC02 -- Politica exacta de retry de webhooks Shopify (PARCIAL)

**Situacao:** A knowledge base menciona que a Shopify re-tenta webhooks mas nao documenta detalhes (numero de tentativas, intervalo entre retries, backoff). O analyst menciona 48h de window.

**Informacao confirmada:**
- Timeout de 5 segundos para resposta
- Retry automatico em caso de falha
- Window de ate 48 horas

**Informacao em falta:**
- Numero exacto de tentativas
- Intervalo entre tentativas (exponencial? fixo?)
- O que acontece apos 48h (webhook e removido? desactivado?)

**Impacto:** Baixo. O nosso servidor deve responder 200 em < 100ms (so enfileira). O cenario de falha e improvavel.

---

### LAC03 -- Documentacao de `fulfillment_status` valores possiveis (PARCIAL)

**Situacao:** A knowledge base em `orders.md` lista `fulfilled`, `unfulfilled`, `partial` como valores de `fulfillment_status`, mas no contexto de parametro de query. No corpo da response, o campo pode ser `null` (que significa unfulfilled).

**Valores confirmados:**
- `null` -- pedido sem fulfillment (equivalente a "unfulfilled")
- `"partial"` -- envio parcial
- `"fulfilled"` -- totalmente enviado

**Impacto:** Baixo. Para o D3, a logica e: se `fulfillment_status` != `"fulfilled"` -> elegivel. Isso cobre `null` e `"partial"`.

---

### LAC04 -- Formato de `created_at` no webhook vs API

**Situacao:** Nao ha documentacao explicita sobre diferenca de formato entre o `created_at` recebido via webhook e o `created_at` obtido via API REST.

**Expectativa (baseada em padroes Shopify):**
- Ambos usam ISO 8601 com timezone offset: `"2026-03-10T10:30:00+00:00"` ou `"2026-03-10T10:30:00-05:00"`
- Para queries com `created_at_min`/`created_at_max`, enviar em formato UTC com sufixo `Z`: `"2026-03-10T10:30:00Z"`

**Impacto:** Baixo. Usar `datetime.fromisoformat()` ou `dateutil.parser.parse()` para parsing defensivo.

---

### LAC05 -- Interface com sistema de Review Request (NAO DEFINIDA)

**Situacao:** A regra SUP05 depende de uma interface com o sistema de Review Request que ainda nao existe. O architect propoe implementacao provisoria com ficheiro JSON.

**Implementacao provisoria (do blueprint):**
- Ficheiro `review_requests.json` com formato `{ "phone": "timestamp_activacao" }`
- Se ficheiro nao existir ou variavel `REVIEW_REQUEST_FILE` vazia, a regra SUP05 e silenciosamente ignorada (nao bloqueia envios)

**Impacto:** Baixo. A implementacao provisoria e suficiente. Quando o sistema de Review Request for implementado, basta actualizar o formato do ficheiro ou migrar para endpoint HTTP.

---

### LAC06 -- Documentacao de erros da Evolution API (PARCIAL)

**Situacao:** A knowledge base documenta o uso da Evolution API mas nao detalha codigos de erro especificos nem mensagens de erro.

**Informacao confirmada:**
- HTTP 200 com payload de sucesso (campos `key`, `message`, `status`)
- Formato de numero incorreto causa erro
- Instancia desconectada causa erro

**Informacao em falta:**
- Codigos HTTP especificos para cada tipo de erro
- Formato do corpo de erro (JSON? texto?)
- Rate limit enforcement e resposta

**Recomendacao:** O @dev deve implementar try/except generico com log do status code e body completo para capturar e documentar erros em producao.

**Impacto:** Medio. O worker deve tratar qualquer excepcao no envio como erro recuperavel e manter o item na fila ou marcar como `"error"`.

---

### LAC07 -- Shopify Webhook `orders/paid` vs `orders/create`

**Situacao:** A knowledge base em `webhooks.md` lista `orders/create` e `orders/paid` como topics disponiveis. Para o D1, usamos `orders/paid` (confirmacao de pagamento), NAO `orders/create` (criacao do pedido).

**Diferenca importante:**
- `orders/create` dispara quando o pedido e criado (pode nao estar pago)
- `orders/paid` dispara quando o pagamento e confirmado (correcto para D1)

**Impacto:** Nenhum. O blueprint ja especifica `orders/paid` correctamente.

---

## Pronto para o @mapper

Todas as APIs e servicos necessarios para o projecto `post-purchase-wpp` foram pesquisados e documentados com base na knowledge base existente. As lacunas identificadas sao de baixo impacto e possuem estrategias de mitigacao definidas.

**Resumo de endpoints a utilizar:**

| API | Endpoints | Total |
|-----|-----------|-------|
| Shopify Admin REST | GET orders.json, GET orders/{id}.json, GET customers/{id}.json, GET custom_collections.json, GET collects.json, POST webhooks.json, GET webhooks.json | 7 |
| Evolution API | POST /message/sendText/{instance}, GET /instance/connectionState/{instance} | 2 |
| Webhook Server (nosso) | POST /webhooks/orders/paid, POST /webhooks/fulfillments/create, GET /health | 3 (a implementar) |

**Total de chamadas API externas distintas:** 9 endpoints (7 Shopify + 2 Evolution)

O @mapper e o @dev possuem agora todas as informacoes de request/response, formatos de dados, autenticacao, rate limits e regras de negocio necessarias para prosseguir com o mapeamento e a implementacao sem consultar documentacao externa.

---

*Documento gerado por @researcher (Rex) em 2026-03-10. Pronto para @mapper.*
