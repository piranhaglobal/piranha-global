# Piranha Global — Configuração AIOX

## Contexto do Projeto
Este é o projeto de desenvolvimento da Piranha Global, uma empresa de automação de negócios.
Trabalhamos com: Shopify, Evolution API (WhatsApp), Ultravox (voice AI + TTS), Twilio / Telnyx (telefonia), Klaviyo (email).

---

## Squads Ativos

| Squad | Nome | Ícone | Prioridade | Status |
|-------|------|-------|-----------|--------|
| `piranha-dev` | Desenvolvimento | ⚙️ | 0 | active |
| `piranha-scraping` | SALES | 🦈 | 1 | active |
| `piranha-design` | Design | 🎨 | 2 | active |
| `piranha-workshops` | WORKSHOPS | 🎓 | 2 | planning |
| `piranha-comms` | COMUNICAÇÃO | 📢 | 3 | active |
| `piranha-supplies` | SUPPLIES | 📦 | 4 | planning |
| `piranha-studio` | ESTÚDIO | 🏢 | 5 | backlog |

---

## Squad: piranha-dev (⚙️ Desenvolvimento)

Pipeline de desenvolvimento Full Stack com IA.

### Pipeline (ordem obrigatória)

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| 1 | architect | `@architect` | Opus | Interpreta o pedido e cria o esboço técnico |
| 2 | researcher | `@researcher` | Sonnet | Pesquisa e compila documentação das APIs |
| 3 | mapper | `@mapper` | Sonnet | Mapeia arquivos, funções e fluxo de dados |
| 4 | dev | `@dev` | Sonnet | Implementa o código seguindo o mapeamento |
| 5 | qa | `@qa` | Sonnet | Revisa e emite APROVADO ou REPROVADO |

### Agentes de Suporte

| Agente | Activation | Papel |
|--------|-----------|-------|
| analyst | `@analyst` | Levantamento de requisitos e análise de negócio |
| pm | `@pm` | Gestão de produto e backlog |
| sm | `@sm` | Criação e organização de stories (Haiku) |

### Fluxos de Trabalho

- **Novo projeto complexo:** `@analyst` → `@architect` → `@researcher` → `@mapper` → `@dev` → `@qa`
- **Script simples:** `@analyst` → `@dev` → `@qa`
- **Debug:** `@qa` → `@dev` → `@qa`
- **Nunca pule etapas** em projetos que envolvam múltiplas APIs

### Quality Gates
- Após `@architect` → aprovação humana obrigatória
- Após `@dev` → revisão do `@qa` obrigatória
- Antes de qualquer deploy em produção → aprovação humana

---

## Squad: piranha-scraping (🦈 SALES)

Squad de vendas — Scraping de leads, qualificação e voice agents.

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| S | analyst-leads | `@analyst` | Sonnet | Levantamento de requisitos e mercados-alvo |
| 1 | scraper-agent | `@scraper` | Sonnet | Scraping de empresas (retalho, PMU, tatuagem) |
| 2 | price-analyst | `@price-analyst` | Sonnet | Análise e scraping de preços para penetração de mercado |
| 3 | leads-qualifier | `@leads-qualifier` | Sonnet | Qualificação e segmentação de leads |
| 4 | voice-agent | `@voice-agent` | Opus | Agente de voz (Ultravox + Telnyx) para outreach |
| 5 | qa-leads | `@qa` | Sonnet | Revisão de qualidade das leads e métricas |

**Integrações:** Shopify, Evolution API, Ultravox, Telnyx, Klaviyo

---

## Squad: piranha-design (🎨 Design)

Squad de Web Design UX/UI — páginas web, visuais de marca e deployment Shopify.
**Marcas:** piranha-supplies, piranha-studios, revolution-needles, meta, piranha-lab

| Step | Agente | Alias | Activation | Modelo | Papel |
|------|--------|-------|-----------|--------|-------|
| - | creative-director | Dara | `@creative-director` | Opus | Head of squad — visão criativa, aprovações, consistência de marca |
| 1 | ux-researcher | Uri | `@ux-researcher` | Sonnet | Research, benchmarks, wireframes, UX patterns |
| 2 | ui-designer | Lia | `@ui-designer` | Sonnet | Design visual, layout, tipografia, componentes |
| 2 | design-system | Kai | `@design-system` | Sonnet | Guardião de tokens, componentes e consistência visual |
| 2 | content-designer | Vera | `@content-designer` | Sonnet | Content hierarchy, UX copy, headings, CTAs |
| 3 | visual-prompt-architect | Zara | `@visual-prompt-architect` | Sonnet | Prompts de imagem AI para secções e fundos |
| 3 | product-scene-builder | Marco | `@product-scene-builder` | Sonnet | Prompts de fotografia de produto AI |
| 3 | page-element-designer | Nyx | `@page-element-designer` | Sonnet | Fundos, texturas, elementos atmosféricos, ícones |
| 4 | html-builder | Rex | `@html-builder` | Sonnet | Frontend — HTML/CSS/JS + Shopify Liquid |
| 5 | qa-visual | Kael | `@qa-visual` | Sonnet | QA — design system, responsivo, acessibilidade |
| 5 | shopify-deployer | Flex | `@shopify-deployer` | Sonnet | HTML→Liquid, asset management, deployment |

### Fases do Workflow
- **Fase 1 — Brief & Research:** `creative-director` + `ux-researcher` → gate: aprovação humana
- **Fase 2 — Design:** `ui-designer` + `design-system` + `content-designer` → gate: aprovação `@creative-director`
- **Fase 3 — Visual Assets (paralelo):** `visual-prompt-architect` + `product-scene-builder` + `page-element-designer`
- **Fase 4 — Build:** `html-builder` → auto-proceed para QA
- **Fase 5 — QA & Deploy:** `qa-visual` + `shopify-deployer` → gate: aprovação humana final

### Regras Críticas de Design
- Nunca iniciar build sem aprovação do `@creative-director`
- Nunca deployer sem aprovação do `@qa-visual` e aprovação humana
- Sempre archive do tema antes de qualquer deploy
- Nenhum valor hardcoded — apenas variáveis CSS do design system
- Brand routing obrigatório antes de qualquer trabalho visual
- Todo código: mobile-first + acessível (WCAG AA mínimo)

---

## Squad: piranha-comms (📢 COMUNICAÇÃO)

Squad de Comunicação 360 — estratégia, canais e distribuição.

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| 1 | head-of-comms | `@head-of-comms` | Opus | Arquitecto de estratégia e planos de comunicação 360 |
| 2 | distributor-agent | `@distributor` | Sonnet | Distribuição de conteúdo validado por todos os canais |
| 3 | social-media-agent | `@social-media` | Sonnet | Conteúdo educacional, técnico, inspiracional e de comunidade |
| 4 | ecommerce-agent | `@ecommerce` | Haiku | Conteúdo para produto, colecções e campanhas Shopify |
| 5 | ads-agent | `@ads-agent` | Sonnet | Criação e optimização de anúncios |
| 6 | blog-writer | `@blog-writer` | Sonnet | Artigos SEO, conteúdo técnico e educacional |
| 7 | email-marketing | `@email-mkt` | Haiku | Segmentação, flows e campanhas Klaviyo |
| 8 | lead-magnets | `@lead-magnets` | Sonnet | E-books, infográficos e conteúdo de captação |

**Pilares de conteúdo:** Educacional · Técnico · Inspiracional · Comunidade
**Integrações:** Shopify, Klaviyo, Instagram Graph API

---

## Squad: piranha-workshops (🎓 WORKSHOPS)

Automatização do funil de Workshops — da captação ao pós-fecho.
> **Nota:** A Daniela fecha por telefone e é muito eficaz. Não automatizar o fecho telefónico. O foco é APÓS o fecho.

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| 1 | blueprint-agent | `@blueprint` | Opus | Radiografia do funil actual e blueprint da jornada do aluno |
| 2 | lp-builder | `@lp-builder` | Sonnet | Landing Page: copy, design Piranha, formulários |
| 3 | ads-workshops | `@ads-workshops` | Sonnet | Estratégia e criação de Ads para captação de leads |
| 4 | crm-automation | `@crm-automation` | Sonnet | Pós-fecho: marcação, sinal, confirmações, vésperas, conteúdos |
| 5 | loyalty-agent | `@loyalty` | Haiku | Tier de fidelização, cupões e segmentação de listas |
| 6 | qa-workshops | `@qa` | Sonnet | Revisão do funil completo e métricas de captação |

**Integrações:** Shopify, Evolution API, Klaviyo

---

## Squad: piranha-supplies (📦 SUPPLIES)

Stocks, Supply Chain, Encomendas e Forecast.

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| 1 | stock-analyst | `@stock-analyst` | Opus | Análise de stocks e classificação ABC |
| 2 | abc-classifier | `@abc-classifier` | Haiku | Classificação ABC por tipologia, zona e fornecedor |
| 3 | leadtime-analyst | `@leadtime-analyst` | Sonnet | Análise diária de lead times da Ásia |
| 4 | supply-chain | `@supply-chain` | Sonnet | Análise e sugestão de compra com custo mínimo |
| 5 | forecast-agent | `@forecast` | Sonnet | Análise de vendas, sazonalidade e forecast |
| 6 | rotation-analyst | `@rotation-analyst` | Haiku | Análise de rotação de linear |
| 7 | admin-compras | `@admin-compras` | Haiku | Lançamento de notas de encomenda por fornecedor |
| 8 | qa-supplies | `@qa` | Sonnet | Supervisão e validação de decisões de compra |

**Objetivos:** Produtos A sempre em stock · Zero out-of-stock · Lead times Ásia ao dia

---

## Squad: piranha-studio (🏢 ESTÚDIO)

Radiografia e automação de processos do Estúdio.

| Step | Agente | Activation | Modelo | Papel |
|------|--------|-----------|--------|-------|
| 1 | studio-analyst | `@studio-analyst` | Opus | Radiografia geral — mapeamento de todos os processos |
| 2 | process-mapper | `@process-mapper` | Sonnet | Mapeamento detalhado — identificação de quick wins |
| 3 | quickwins-agent | `@quickwins` | Sonnet | Selecção e priorização de quick wins |
| 4 | ops-agent | `@ops-agent` | Sonnet | Operacionalização e automação dos processos |
| 5 | cx-agent | `@cx-agent` | Haiku | Monitorização de experiência pós-implementação |
| 6 | qa-studio | `@qa` | Sonnet | Revisão e escalabilidade dos processos |

---

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

---

## Regras de Negócio Globais

- Todo código Python segue os padrões em `squads/piranha-dev/agents/dev-piranha.md`
- Knowledge base fica em `knowledge/` — **todos os agentes** devem consultar antes de assumir
- Repositórios de referência em `knowledge/repos/`:
  - `andrej-karpathy-skills` — skills/prompts técnicos de LLMs (Karpathy)
  - `GenericAgent` — framework de agentes genéricos com ferramentas web
  - `hermes-agent` — framework Hermes multi-agente (NousResearch)
  - `claude-mem` — padrões de memória persistente para agentes Claude
  - `evolver` — sistema de evolução e optimização de agentes
- Nunca faça deploy sem aprovação humana
- Modelos: `Haiku`=execução/automação, `Sonnet`=padrão, `Opus`=estratégico/irreversível
- Todas as integrações críticas: Shopify · Evolution API (WhatsApp) · Ultravox · Telnyx · Klaviyo

## Design System Governance

1. Antes de qualquer tarefa de front-end, UI, landing page, dashboard, componente, interface, website, Shopify theme, newsletter visual ou app interna, ler obrigatoriamente o ficheiro `DESIGN.md`.
2. Nenhum agente deve inventar cores, tipografia, espaçamentos, componentes ou linguagem visual fora do `DESIGN.md`.
3. Se um projeto exigir uma exceção visual, o agente deve justificar a exceção e propor atualização ao `DESIGN.md`.
4. O `@architect` deve considerar o `DESIGN.md` na arquitetura de qualquer feature visual.
5. O `@dev` deve aplicar os tokens no código.
6. O `@qa` deve validar consistência visual contra o `DESIGN.md`.
7. Se o trabalho for apenas back-end, o `DESIGN.md` não precisa bloquear a execução, mas deve ser considerado se houver qualquer output visual.
8. Para projetos com sub-marcas, o agente deve identificar primeiro se está a trabalhar para Piranha Global, Piranha Tattoo Supplies, Piranha Tattoo Studios, Piranha LAB, Revolution Needles, Meta/Workstation, Piranha Originals ou Safe Tat.

## Language
Sempre responda em português brasileiro.
