# Telnyx API — Overview

## O que é
API de telefonia para SMS, ligações programáticas, conferência e SIP.
Integra nativamente com Ultravox para chamadas com IA.

## Base URL
```
https://api.telnyx.com/v2
```

## Autenticação
```
Authorization: Bearer {TELNYX_API_KEY}
Content-Type: application/json
```

## Casos de Uso na Piranha Global
- Enviar SMS transacionais (confirmações, lembretes)
- Fazer ligações automatizadas com Ultravox
- Receber chamadas e rotear para agente IA

## Documentação Oficial
https://developers.telnyx.com

## Rate Limits
- SMS: 10 mensagens/segundo por número
- Chamadas: 10 chamadas simultâneas no plano básico
