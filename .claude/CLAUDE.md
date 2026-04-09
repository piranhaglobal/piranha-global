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

## Integração com Pixel Agents UI (OBRIGATÓRIO)

**SEMPRE** que activares um agente do pipeline, executa o signal ANTES de fazer o trabalho:

```bash
# Início de cada fase — executa PRIMEIRO, depois trabalha
python3 squads/piranha-dev/claude_signal.py @architect "A analisar o pedido e criar esboço técnico..."
python3 squads/piranha-dev/claude_signal.py @researcher "A pesquisar documentação das APIs..."
python3 squads/piranha-dev/claude_signal.py @mapper "A mapear ficheiros, funções e fluxo de dados..."
python3 squads/piranha-dev/claude_signal.py @dev "A implementar o código..."
python3 squads/piranha-dev/claude_signal.py @qa "A rever o código e emitir parecer..."

# Agentes de suporte
python3 squads/piranha-dev/claude_signal.py @analyst "A levantar requisitos..."
python3 squads/piranha-dev/claude_signal.py @pm "A gerir produto e backlog..."
python3 squads/piranha-dev/claude_signal.py @sm "A criar e organizar stories..."

# Fim do pipeline
python3 squads/piranha-dev/claude_signal.py --status completed

# Início de nova tarefa (limpa logs anteriores)
python3 squads/piranha-dev/claude_signal.py --reset
```

Esta integração faz os personagens pixel art aparecerem a trabalhar nas mesas na UI em tempo real.
O squad-server.js deve estar a correr: `node squad-server.js` (porta 3001).

## Regras de Negócio
- Todo código Python segue os padrões em `squads/piranha-dev/agents/dev-piranha.md`
- Knowledge base fica em `knowledge/` — o @researcher sempre consulta antes de assumir
- Nunca faça deploy sem aprovação humana
- Modelos: Haiku=execução, Sonnet=padrão, Opus=estratégico (architect)

## Language
Sempre responda em português brasileiro.
