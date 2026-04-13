# Iniciativa: Disparador Voice Agent - Abandoned Checkout
**Equipa:** Piranha Supplies (Voice & E-commerce)  |  **Última Atualização:** 13/04/2026

---

## Indicadores & Objetivos

### Disparador Voice Agent - Abandoned Checkout
- **Sistema de recuperação de checkouts abandonados via agente IA com voz — Ultravox + Twilio**
- **Dois momentos de contacto: 7º dia (urgência) + retry automático para sem resposta (7º dia útil)**
- **Status: Operacional — estrutura completa, 17 chamadas testadas, 64.7% conversão validada**

---

## Ações Futuras

### Disparador Voice Agent - Abandoned Checkout
- **Sistema estável — retry automático + janela horária GDPR em progresso**

---

## Principais Ações Implementadas

### Disparador Voice Agent - Abandoned Checkout
- **Automação cron operacional com recuperação em 1 etapa (7º dia), multilingue (PT, ES, FR, EN), deduplicada, deployed e a gerar logs em https://call.piranhasupplies.com/admin/calls**
- **Cron fix (operator shell inválido removido) + phone normalization E.164 (27 países EU)**
- **Gravação Ultravox + audio proxy servidor-side + transcrição + playback no dashboard**
- **Webhook tools: warm transfer + log call result integradas no system prompt do agente**
- **Docker Swarm VPS 144.91.85.135, health checks, VAD otimizado para µ-law 8kHz Twilio**

---

## Decisões Necessárias & Constrangimentos

- **Horário de chamadas GDPR-compliant (9-17h) + retry automático em progresso**

---

**Última Validação:** 2026-04-13 | **Próxima Review:** 2026-04-20
