# Shopify — Pedidos (Orders)

## Endpoint
```
GET /admin/api/2024-10/orders.json
```

## Parâmetros Principais

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `status` | string | `open`, `closed`, `cancelled`, `any` |
| `financial_status` | string | `paid`, `pending`, `refunded`, `partially_paid` |
| `fulfillment_status` | string | `fulfilled`, `unfulfilled`, `partial` |
| `created_at_min` | datetime | Pedidos após esta data |
| `limit` | integer | Máximo 250 |

## Exemplo Python
```python
def get_recent_orders(hours: int = 24, status: str = "any") -> list:
    """Busca pedidos recentes."""
    since = datetime.utcnow() - timedelta(hours=hours)

    url = f"https://{STORE_URL}/admin/api/{VERSION}/orders.json"
    params = {
        "status": status,
        "created_at_min": since.isoformat() + "Z",
        "limit": 250
    }

    response = requests.get(url, headers=HEADERS, params=params)
    return response.json().get("orders", [])
```

## Campos Importantes
- `id`, `name` (ex: #1001), `email`, `phone`
- `customer.first_name`, `customer.last_name`
- `total_price`, `currency`
- `financial_status` — status de pagamento
- `fulfillment_status` — status de envio
- `line_items` — produtos comprados
- `shipping_address` — endereço de entrega
