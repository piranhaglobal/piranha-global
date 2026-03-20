# Shopify — Carrinhos Abandonados

## Endpoint
```
GET /admin/api/2024-10/checkouts.json
```

## Autenticação
```
X-Shopify-Access-Token: {SHOPIFY_ACCESS_TOKEN}
```

## Parâmetros de Busca

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `created_at_min` | datetime | Mínimo de criação | `2024-01-01T00:00:00Z` |
| `created_at_max` | datetime | Máximo de criação | `2024-01-31T23:59:59Z` |
| `updated_at_min` | datetime | Mínimo de atualização | - |
| `since_id` | integer | Carrinhos após este ID | - |
| `limit` | integer | Itens por página (máx 250) | `100` |
| `status` | string | `open` (padrão) | `open` |

## Exemplo de Requisição Python
```python
import requests
from datetime import datetime, timedelta

def get_abandoned_checkouts(hours: int = 2) -> list:
    """Busca carrinhos abandonados nas últimas X horas."""
    store_url = os.getenv("SHOPIFY_STORE_URL")
    token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    version = os.getenv("SHOPIFY_API_VERSION", "2024-10")

    since = datetime.utcnow() - timedelta(hours=hours)

    url = f"https://{store_url}/admin/api/{version}/checkouts.json"
    headers = {"X-Shopify-Access-Token": token}
    params = {
        "created_at_min": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 250,
        "status": "open"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json().get("checkouts", [])
```

## Exemplo de Resposta
```json
{
  "checkouts": [
    {
      "id": 450789469,
      "token": "exampletoken123",
      "cart_token": "68778783ad298f1c80c3bafcddeea02f",
      "email": "cliente@exemplo.com",
      "phone": "+5511999999999",
      "created_at": "2024-01-15T10:30:00-05:00",
      "updated_at": "2024-01-15T10:45:00-05:00",
      "completed_at": null,
      "line_items": [
        {
          "title": "Nome do Produto",
          "quantity": 1,
          "price": "199.90",
          "variant_title": "Tamanho M"
        }
      ],
      "customer": {
        "id": 207119551,
        "first_name": "João",
        "last_name": "Silva",
        "email": "joao@exemplo.com",
        "phone": "+5511999999999"
      },
      "subtotal_price": "199.90",
      "total_price": "219.90",
      "currency": "BRL",
      "abandoned_checkout_url": "https://checkout.shopify.com/...",
      "discount_codes": []
    }
  ]
}
```

## Campos Importantes
- `email` — email do cliente
- `phone` — telefone (formato internacional: +55...)
- `customer.first_name` — nome para personalizar mensagem
- `abandoned_checkout_url` — link para recuperar o carrinho
- `total_price` — valor total
- `line_items` — produtos no carrinho

## Atenção
- `completed_at: null` significa que o checkout NÃO foi concluído (abandonado)
- Telefone pode não estar preenchido — sempre verifique antes de enviar
- Shopify não tem endpoint específico "abandoned" — filtre por `completed_at: null` nos checkouts `open`
