"""
Orquestrador Piranha Global
Injeta knowledge base automaticamente baseado no pedido do usuário.
Uso: python orchestrator.py
"""

import os
import re
import sys
import time
import json
from pathlib import Path
from typing import Set
import anthropic

HEADLESS_MODE = '--headless' in sys.argv
DATA_DIR = Path(__file__).parent / "data"

def log_event(agent: str, action: str):
    if not HEADLESS_MODE:
        return
    DATA_DIR.mkdir(exist_ok=True)
    logs_file = DATA_DIR / "logs.jsonl"
    with open(logs_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "time": time.strftime("%H:%M:%S"),
            "agent": agent,
            "action": action
        }) + "\n")

def request_human_approval(prompt: str) -> str:
    if not HEADLESS_MODE:
        return input(f"\n{prompt} (s/n): ").strip().lower()
    
    DATA_DIR.mkdir(exist_ok=True)
    state_file = DATA_DIR / "state.json"
    
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({
            "status": "waiting_human_approval",
            "prompt": prompt
        }, f)
    
    log_event("@human", "Pipeline pausada no Quality Gate. A aguardar aprovação humana...")
    
    while True:
        time.sleep(1)
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if state.get("status") == "resolved":
                    decision = state.get("decision", "n").lower()
                    state_file.unlink()
                    log_event("@human", f"Decisão aprovada? {decision.upper()}")
                    return decision
            except Exception:
                pass

# ===================================================
# CONFIGURAÇÃO DE MODELOS (Economia de Tokens)
# ===================================================
MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",    # Execução, busca, formatação
    "sonnet": "claude-sonnet-4-5-20251001",    # Análise, código, escrita
    "opus":   "claude-opus-4-6",               # Estratégia, arquitetura crítica
}

# Modelo por agente
AGENT_MODELS = {
    "analyst":    MODELS["sonnet"],
    "architect":  MODELS["opus"],
    "dev":        MODELS["sonnet"],
    "qa":         MODELS["sonnet"],
    "sm":         MODELS["haiku"],
    "pm":         MODELS["sonnet"],
    "default":    MODELS["sonnet"],
}

# ===================================================
# MAPEAMENTO DE KNOWLEDGE BASE
# ===================================================
KNOWLEDGE_MAP = {
    # Shopify
    "shopify":     ["apis/shopify/overview.md", "apis/shopify/orders.md"],
    "carrinho":    ["apis/shopify/abandoned-checkouts.md"],
    "abandoned":   ["apis/shopify/abandoned-checkouts.md"],
    "loja":        ["apis/shopify/overview.md"],
    "pedido":      ["apis/shopify/orders.md"],
    "cliente":     ["apis/shopify/customers.md"],
    "produto":     ["apis/shopify/products.md"],
    "webhook":     ["apis/shopify/webhooks.md"],

    # Evolution API
    "whatsapp":    ["apis/evolution-api/send-message.md", "apis/evolution-api/instances.md"],
    "evolution":   ["apis/evolution-api/send-message.md", "apis/evolution-api/instances.md"],
    "mensagem":    ["apis/evolution-api/send-message.md"],
    "instancia":   ["apis/evolution-api/instances.md"],
    "grupos":      ["apis/evolution-api/groups.md"],

    # Ultravox
    "ultravox":    ["apis/ultravox/overview.md", "apis/ultravox/calls.md"],
    "ligacao":     ["apis/ultravox/calls.md"],
    "chamada":     ["apis/ultravox/calls.md"],
    "voz":         ["apis/ultravox/overview.md", "apis/cartesia/overview.md"],

    # Cartesia
    "cartesia":    ["apis/cartesia/overview.md", "apis/cartesia/tts.md"],
    "tts":         ["apis/cartesia/tts.md"],
    "audio":       ["apis/cartesia/tts.md"],
    "sonic":       ["apis/cartesia/tts.md"],

    # Telnyx
    "telnyx":      ["apis/telnyx/overview.md", "apis/telnyx/sms.md"],
    "sms":         ["apis/telnyx/sms.md"],
    "telefone":    ["apis/telnyx/calls.md"],
    "call":        ["apis/telnyx/calls.md"],

    # Infraestrutura
    "cron":        ["infraestrutura/cron-patterns.md"],
    "agendar":     ["infraestrutura/cron-patterns.md"],
    "deploy":      ["infraestrutura/vps-endpoints.md"],
    "vps":         ["infraestrutura/vps-endpoints.md"],
    "python":      ["infraestrutura/python-patterns.md"],

    # Negócio
    "horario":     ["negocio/regras-de-mensagem.md"],
    "tom":         ["negocio/regras-de-mensagem.md"],
    "fluxo":       ["negocio/fluxos-de-automacao.md"],
}

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "knowledge"


def get_relevant_knowledge(user_request: str) -> str:
    """
    Detecta quais arquivos da knowledge base são relevantes para o pedido.
    Retorna o conteúdo concatenado desses arquivos.
    """
    request_lower = user_request.lower()
    files_to_load: Set[str] = set()

    for keyword, files in KNOWLEDGE_MAP.items():
        if keyword in request_lower:
            files_to_load.update(files)

    if not files_to_load:
        return ""

    knowledge = "\n\n---\n# KNOWLEDGE BASE RELEVANTE\n"
    loaded = []

    for filepath in sorted(files_to_load):
        full_path = KNOWLEDGE_BASE_PATH / filepath
        if full_path.exists():
            knowledge += f"\n\n## {filepath}\n"
            knowledge += full_path.read_text(encoding="utf-8")
            loaded.append(filepath)
        else:
            # Arquivo não criado ainda — avisa sem travar
            knowledge += f"\n\n## {filepath}\n[Arquivo não encontrado. Crie em knowledge/{filepath}]\n"

    if loaded:
        print(f"Knowledge base injetada: {', '.join(loaded)}")

    return knowledge


def load_agent_prompt(agent_name: str) -> str:
    """Carrega o prompt de um agente do squad piranha-dev."""
    prompt_path = Path(__file__).parent / "agents" / f"{agent_name}-piranha.md"

    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    # Fallback para agentes base do AIOX
    base_path = Path(__file__).parent.parent.parent / ".aiox-core" / "core" / "agents" / f"{agent_name}.md"
    if base_path.exists():
        return base_path.read_text(encoding="utf-8")

    return f"Você é o agente {agent_name} da Piranha Global. Responda em português."


def call_agent(
    agent_name: str,
    user_message: str,
    context: str = "",
    inject_knowledge: bool = True
) -> str:
    """
    Chama um agente específico com o contexto e knowledge base adequados.

    Args:
        agent_name: Nome do agente (analyst, architect, dev, qa, sm, pm)
        user_message: Mensagem/pedido do usuário
        context: Contexto adicional (output de agentes anteriores)
        inject_knowledge: Se deve injetar knowledge base automaticamente

    Returns:
        Resposta do agente como string
    """
    client = anthropic.Anthropic()
    model = AGENT_MODELS.get(agent_name, AGENT_MODELS["default"])

    # Carrega prompt do agente
    system_prompt = load_agent_prompt(agent_name)

    # Injeta knowledge base se relevante
    knowledge = ""
    if inject_knowledge:
        if agent_name in ["analyst", "architect"]:
            knowledge = get_relevant_knowledge(user_message)
        elif agent_name == "dev":
            knowledge = get_relevant_knowledge(context or user_message)

    # Monta a mensagem completa
    full_message = user_message
    if context:
        full_message = f"## Contexto do Agente Anterior:\n{context}\n\n## Sua Tarefa:\n{user_message}"
    if knowledge:
        full_message = f"{full_message}\n\n{knowledge}"

    print(f"\nChamando @{agent_name} ({model})...")

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": full_message}
        ]
    )

    return response.content[0].text


def run_pipeline(user_request: str) -> dict:
    outputs = {}

    print(f"\nINICIANDO PIPELINE PIRANHA")
    print(f"Pedido: {user_request[:100]}...")
    print("=" * 60)
    log_event("system", f"Iniciando Pipeline Piranha com o pedido: {user_request[:50]}...")

    # Fase 1: Analyst levanta requisitos
    print("\nFASE 1: Levantamento de Requisitos (@analyst)")
    log_event("@analyst-piranha", "Iniciando levantamento de requisitos e compilação de dados...")
    outputs["analyst"] = call_agent("analyst", user_request, inject_knowledge=True)
    log_event("@analyst-piranha", "Requisitos levantados com sucesso.")
    print("Analyst concluído")

    # Quality Gate 1: Exibir para humano
    print("\n" + "=" * 60)
    print("OUTPUT DO ANALYST:")
    print(outputs["analyst"])
    print("=" * 60)

    continuar = request_human_approval("Continuar para a Arquitetura?")
    if continuar != 's':
        print("Pipeline pausado pelo usuário.")
        log_event("system", "Pipeline abortada pelo utilizador no Gate do Analyst.")
        return outputs

    # Fase 2: Architect desenha a solução
    print("\nFASE 2: Arquitetura da Solução (@architect)")
    log_event("@architect-piranha", "A desenhar a arquitetura da solução baseada nos requisitos...")
    outputs["architect"] = call_agent(
        "architect",
        f"Com base nos seguintes requisitos, crie a arquitetura completa:\n\n{outputs['analyst']}",
        context=outputs["analyst"],
        inject_knowledge=True
    )
    log_event("@architect-piranha", "Esboço arquitetural concluído.")
    print("Architect concluído")

    # Quality Gate 2: Aprovação humana da arquitetura
    print("\n" + "=" * 60)
    print("OUTPUT DO ARCHITECT:")
    print(outputs["architect"])
    print("=" * 60)

    continuar = request_human_approval("Aprovado o esquema? Continuar para o desenvolvimento?")
    if continuar != 's':
        print("Pipeline pausado pelo usuário.")
        log_event("system", "Pipeline abortada pelo utilizador no Gate do Architect.")
        return outputs

    # Fase 3: Dev escreve o código
    print("\nFASE 3: Desenvolvimento do Código (@dev)")
    log_event("@dev-piranha", "A codificar e implementar o sistema focado nos padrões de design definidos...")
    outputs["dev"] = call_agent(
        "dev",
        f"Implemente o código Python completo com base na arquitetura aprovada:\n\n{outputs['architect']}",
        context=outputs["architect"],
        inject_knowledge=True
    )
    log_event("@dev-piranha", "Implementação base do código terminada.")
    print("Dev concluído")

    # Fase 4: QA revisa
    print("\nFASE 4: Revisão de Qualidade (@qa)")
    log_event("@qa-piranha", "Iniciando revisão sintática e boas métricas...")
    outputs["qa"] = call_agent(
        "qa",
        f"Revise o seguinte código Python para o projeto da Piranha Global:\n\n{outputs['dev']}",
        context=outputs["dev"],
        inject_knowledge=False
    )
    log_event("@qa-piranha", "Revisão e Quality Assurance completadas.")
    print("QA concluído")

    # Resultado final
    print("\n" + "=" * 60)
    print("RESULTADO FINAL DO QA:")
    print(outputs["qa"])
    print("=" * 60)
    log_event("system", "Pipeline concluída com 100% de êxito! Os recursos foram gerados.")

    # Salvar output
    save_output(user_request, outputs)

    return outputs


def save_output(request: str, outputs: dict, filename: str = None):
    """Salva os outputs do pipeline em um arquivo markdown."""
    output_dir = Path("projetos_gerados")
    output_dir.mkdir(exist_ok=True)

    if not filename:
        safe_name = re.sub(r'[^a-z0-9]+', '-', request[:40].lower()).strip('-')
        filename = f"{safe_name}.md"

    filepath = output_dir / filename

    import datetime
    content = f"""# Pipeline: {request[:60]}

**Data:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Requisitos (Analyst)
{outputs.get('analyst', 'N/A')}

---

## Arquitetura (Architect)
{outputs.get('architect', 'N/A')}

---

## Código (Dev)
{outputs.get('dev', 'N/A')}

---

## Revisão QA
{outputs.get('qa', 'N/A')}
"""

    filepath.write_text(content, encoding="utf-8")
    print(f"\nOutput salvo em: {filepath}")


def interactive_mode():
    """Modo interativo — usuário faz pedidos diretamente."""
    print("\n" + "=" * 60)
    print("PIRANHA GLOBAL — Orquestrador de Desenvolvimento IA")
    print("=" * 60)
    print("\nModos disponíveis:")
    print("  1. Pipeline completo (analyst -> architect -> dev -> qa)")
    print("  2. Chamar agente específico")
    print("  3. Sair\n")

    while True:
        modo = input("Escolha o modo (1/2/3): ").strip()

        if modo == "3":
            break

        elif modo == "1":
            pedido = input("\nDescreva o que precisa construir:\n> ").strip()
            if pedido:
                run_pipeline(pedido)

        elif modo == "2":
            print("\nAgentes disponíveis: analyst, architect, dev, qa, sm, pm")
            agente = input("Qual agente? ").strip().lower()
            pedido = input("Mensagem: ").strip()

            if agente and pedido:
                resposta = call_agent(agente, pedido)
                print(f"\n{resposta}")

        continuar = input("\nNova tarefa? (s/n): ").strip().lower()
        if continuar != 's':
            break

    print("\nAte logo!")


if __name__ == "__main__":
    if HEADLESS_MODE:
        idx = sys.argv.index('--headless')
        req = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "Executar pipeline padrão Piranha"
        log_event("system", "Iniciando processo orchestrator (Headless Mode)...")
        run_pipeline(req)
    else:
        interactive_mode()
