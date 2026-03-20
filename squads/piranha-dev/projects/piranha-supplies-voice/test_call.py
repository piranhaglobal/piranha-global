"""
Script de teste — dispara uma chamada real ao número configurado abaixo.
O agente de IA da Piranha Supplies vai falar com quem atender.

Uso:
    python test_call.py
"""

import requests

# ─── CONFIGURAÇÃO DO TESTE ─────────────────────────────────────
VPS_URL = "https://call.piranhasupplies.com"

# Número que vai RECEBER a chamada (o teu telemóvel)
TEST_TO_NUMBER = "+351965559253"

# Contexto fictício — edita à vontade para testar cenários diferentes
TEST_CHECKOUT = {
    "to_number":    TEST_TO_NUMBER,
    "name":         "Vinycius",
    "country_code": "PT",
    "products": [
        {"title": "Kwadron Equaliser Neutron2 Black", "price": ""},
    ],
    "total_price": "100.00",
}
# ───────────────────────────────────────────────────────────────


def run():
    print("=== Piranha Supplies Voice — Chamada de Teste ===\n")
    print(f"Destino  : {TEST_TO_NUMBER}")
    print(f"Cliente  : {TEST_CHECKOUT['name']} ({TEST_CHECKOUT['country_code']})")
    print(f"Produtos : {[p['title'] for p in TEST_CHECKOUT['products']]}")
    print(f"Total    : {TEST_CHECKOUT['total_price']}€\n")
    print("A disparar chamada...")

    resp = requests.post(f"{VPS_URL}/admin/test-call", json=TEST_CHECKOUT, timeout=15)

    if resp.status_code == 202:
        print(f"✓ Chamada iniciada! O teu telefone ({TEST_TO_NUMBER}) irá tocar em breve.")
        print("\nPara ver os logs em tempo real:")
        print("  ssh root@144.91.85.135 'docker service logs piranha-voice_piranha_voice -f --tail 50'")
    else:
        print(f"✗ Erro {resp.status_code}: {resp.text}")


if __name__ == "__main__":
    run()
