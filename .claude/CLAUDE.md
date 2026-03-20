# Piranha Global — Configuração AIOX

## Contexto do Projeto
Este é o projeto de desenvolvimento da Piranha Global, uma empresa de automação de negócios.
Trabalhamos com: Shopify, Evolution API (WhatsApp), Ultravox (voice AI + TTS), Twilio (telefonia).

## Pipeline de Desenvolvimento (ordem obrigatória)

| Step | Agente | Papel |
|------|--------|-------|
| 1 | `@architect` | Interpreta o pedido e cria o esboço técnico |
| 2 | `@researcher` | Pesquisa e compila documentação das APIs |
| 3 | `@mapper` | Mapeia arquivos, funções e fluxo de dados |
| 4 | `@dev` | Implementa o código seguindo o mapeamento |
| 5 | `@qa` | Revisa e emite APROVADO ou REPROVADO |

## Agentes de Suporte
- `@analyst` — levantamento de requisitos antes do pipeline
- `@pm` — gestão de produto e backlog
- `@sm` — criação e organização de stories

## Como Usar
- **Novo projeto complexo:** `@analyst` → `@architect` → `@researcher` → `@mapper` → `@dev` → `@qa`
- **Script simples:** `@dev` direto com contexto suficiente
- **Debug:** `@qa` → `@dev` → `@qa`
- **Nunca pule etapas** em projetos que envolvam múltiplas APIs

## Regras de Negócio
- Todo código Python segue os padrões em `squads/piranha-dev/agents/dev-piranha.md`
- Knowledge base fica em `knowledge/` — o @researcher sempre consulta antes de assumir
- Nunca faça deploy sem aprovação humana
- Modelos: Haiku=execução, Sonnet=padrão, Opus=estratégico (architect)

## Language
Sempre responda em português brasileiro.
