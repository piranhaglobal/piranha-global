"""
Supermemory Quickstart — Piranha Global
Testa as 3 operações principais: add, profile e search
"""

import os
from supermemory import Supermemory

API_KEY = os.environ.get("SUPERMEMORY_API_KEY")
if not API_KEY:
    raise ValueError("Defina a variável de ambiente SUPERMEMORY_API_KEY")
client = Supermemory(api_key=API_KEY)

CONTAINER = "piranha_global_test"


def step1_adicionar_memoria():
    print("\n[1] Adicionando memória...")
    result = client.add(
        content="A Piranha Global usa Evolution API para WhatsApp, Ultravox para voz AI e TTS, e Twilio para telefonia. O squad principal é o Piranha Dev.",
        container_tag=CONTAINER,
        metadata={"source": "quickstart", "projeto": "piranha-global"}
    )
    print(f"    ✓ Memória adicionada — ID: {getattr(result, 'id', result)}")
    return result


def step2_buscar_perfil():
    print("\n[2] Buscando perfil/contexto...")
    response = client.profile(
        container_tag=CONTAINER,
        q="Quais tecnologias a Piranha Global usa?"
    )
    static = getattr(response.profile, "static", []) if hasattr(response, "profile") else response.get("profile", {}).get("static", [])
    dynamic = getattr(response.profile, "dynamic", []) if hasattr(response, "profile") else response.get("profile", {}).get("dynamic", [])
    print(f"    Perfil estático: {static}")
    print(f"    Contexto dinâmico: {dynamic}")
    return response


def step3_buscar_memorias():
    print("\n[3] Buscando memórias por semântica...")
    response = client.search.memories(
        q="WhatsApp e telefonia",
        container_tag=CONTAINER,
    )
    results = getattr(response, "results", response) if not isinstance(response, dict) else response.get("results", [])
    print(f"    Resultados encontrados: {len(results) if hasattr(results, '__len__') else '?'}")
    if results:
        first = results[0] if not isinstance(results, dict) else results
        print(f"    Primeiro resultado: {first}")
    return response


if __name__ == "__main__":
    print("=" * 50)
    print("  Supermemory Quickstart — Piranha Global")
    print("=" * 50)

    step1_adicionar_memoria()
    step2_buscar_perfil()
    step3_buscar_memorias()

    print("\n✓ Quickstart concluído com sucesso!")
