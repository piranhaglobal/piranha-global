# Shopify Admin API — Overview

## Base URL
```
https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}/
```
Exemplo: `https://minha-loja.myshopify.com/admin/api/2024-10/`

## Autenticação
**Header obrigatório:**
```
X-Shopify-Access-Token: {SHOPIFY_ACCESS_TOKEN}
Content-Type: application/json
```

## Versão Atual
`2024-10` (última estável — Q4 2024)

## Rate Limits
- **REST API**: 40 requisições/segundo por app (por loja)
- **Bucket size**: 80 requests
- **Resposta com rate limit**: HTTP 429
- **Header de controle**: `X-Shopify-Shop-Api-Call-Limit: 32/40`

## Padrão de Resposta
```json
{
  "recurso": {
    "id": 123456789,
    "created_at": "2024-01-15T10:30:00-05:00",
    "updated_at": "2024-01-15T11:00:00-05:00"
  }
}
```

## Paginação
```
GET /orders.json?limit=250&page_info={cursor}
```
- Máximo: 250 itens por página
- Use `Link` header para navegar páginas

## Endpoints Mais Usados na Piranha Global
- `GET /checkouts.json` — carrinhos (inclui abandonados)
- `GET /orders.json` — pedidos
- `GET /customers.json` — clientes
- `GET /products.json` — produtos
- `POST /webhooks.json` — criar webhooks

## Documentação Oficial
https://shopify.dev/docs/api/admin-rest
