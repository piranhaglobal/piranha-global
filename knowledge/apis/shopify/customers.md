# Shopify — Clientes (Customers)

## Endpoints
```
GET  /admin/api/2024-10/customers.json
GET  /admin/api/2024-10/customers/{id}.json
POST /admin/api/2024-10/customers/{id}/metafields.json
```

## Buscar Clientes
```python
def search_customer(query: str) -> list:
    """Busca clientes por email ou telefone."""
    url = f"https://{STORE_URL}/admin/api/{VERSION}/customers/search.json"
    params = {"query": query, "limit": 10}

    response = requests.get(url, headers=HEADERS, params=params)
    return response.json().get("customers", [])

# Exemplo: buscar por telefone
clientes = search_customer("phone:+5511999999999")
```

## Campos do Cliente
- `id`, `first_name`, `last_name`, `email`, `phone`
- `orders_count` — total de pedidos
- `total_spent` — total gasto
- `tags` — tags do cliente
- `note` — observações internas
