# Pixel Agents — Integração com o Piranha Global

Este projeto já contém uma integração mínima com a extensão **Pixel Agents** (VS Code) para permitir visualizar o "escritório" (squads/agents) diretamente no painel da extensão.

## O que foi feito

✅ **Layout do escritório**: conseguimos gerar um arquivo `~/.pixel-agents/layout.json` customizado com as salas / mesas de cada squad (Leads, Workshops, Comms, Supplies, Studio) + uma sala de reunião.

✅ **Sessão de demonstração**: geramos um arquivo JSONL de exemplo (`~/.claude/projects/<hash>/demo-*.jsonl`) para o Pixel Agents adotar automaticamente como um "agent" (terminal Claude) e exibir uma conversa inicial.

## Como usar

1. Abra este repositório no VS Code.
2. Execute o script abaixo (dentro do diretório do projeto):

```bash
node scripts/pixel-agents-setup.js --demo
```

Isso vai:
- criar/atualizar `~/.pixel-agents/layout.json` com o layout do escritório Piranha;
- posicionar automaticamente mesas/cadeiras/PCs conforme o número de agents definidos em `squads/<nome-do-squad>/agents`;
- criar um arquivo demo de sessão JSONL em `~/.claude/projects/<hash>/`.

> Para gerar uma sessão por agente (uma “personagem” por arquivo MD do squad), rode:
>
> ```bash
> node scripts/pixel-agents-setup.js --agents
> ```
>
> Depois, abra o painel Pixel Agents, clique em **+ Agent** para cada agente que quiser adicionar, e copie/cole o comando `claude --session-id <id>` listado pelo script em cada terminal.

3. Abra o painel **Pixel Agents** no VS Code (pode procurar por "Pixel Agents" na paleta de comandos ou no sidebar).
4. Na extensão, você deve ver o escritório com os conjuntos de mesas e o "agent" de demonstração.

---

## Se quiser reverter

O script faz backup automático do layout anterior em `~/.pixel-agents/layout.backup-<timestamp>.json`.

```bash
cp ~/.pixel-agents/layout.backup-<timestamp>.json ~/.pixel-agents/layout.json
```

---

## Posso customizar ainda mais?

Sim! Você pode editar o script `scripts/pixel-agents-setup.js` para posicionar mesas e cadeiras em outros pontos da grade, alterar cores ou adicionar itens decorativos.

Se quiser que a extensão mostre agentes reais (não apenas o demo), basta abrir/usar um terminal Claude (`claude --session-id <uuid>`) dentro do workspace; o Pixel Agents vai detectar o JSONL e animar o personagem.
