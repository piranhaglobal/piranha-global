# Ultravox API — Overview

## O que é
API para criar agentes de voz com IA para ligações telefônicas automatizadas.
O agente fala e entende fala (speech-to-speech em tempo real).

## Base URL
```
https://api.ultravox.ai/api
```

## Autenticação
```
X-API-Key: {ULTRAVOX_API_KEY}
Content-Type: application/json
```

## Casos de Uso na Piranha Global
- Ligações de recuperação de carrinho abandonado
- Confirmação de pedidos
- Pesquisas de satisfação
- Suporte automatizado via telefone

## Documentação Oficial
https://docs.ultravox.ai

## Modelos Disponíveis
- `fixie-ai/ultravox` — modelo padrão (baixa latência, alta qualidade)
- `fixie-ai/ultravox-70B` — modelo avançado

## Integração com Telnyx
Ultravox se integra com Telnyx para fazer ligações reais.
