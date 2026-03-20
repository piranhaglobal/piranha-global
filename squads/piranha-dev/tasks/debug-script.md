# Task: Debug de Script Existente

## Objetivo
Investigar e corrigir erros em scripts Python existentes.

## Workflow
1. Cole o código com o erro
2. `@qa *review-build` — QA identifica o problema
3. `@dev *apply-qa-fix` — Dev corrige
4. Você testa a correção

## Input Necessário
- Código Python com problema
- Mensagem de erro (stack trace completo)
- Comportamento esperado vs comportamento atual

## Modelo Usado
- @qa: **claude-sonnet-4-5** (análise de código)
- @dev: **claude-sonnet-4-5** (correção)
