# Iniciativa: Disparador Voice Agent - Abandoned Checkout
**Equipa:** Piranha Supplies (Voice & E-commerce)  |  **Última Atualização:** 13/04/2026

---

## Indicadores & Objetivos

### Disparador Voice Agent - Abandoned Checkout
- **Descrição:** Sistema de recuperação de checkouts abandonados via agente de voz IA (Ultravox + Twilio)
- **Targets:** Contactar leads 7 dias após abandono, intervalo de 10 minutos (scalável)
- **Status:** ✅ Operacional — estrutura completa, métricas validadas em produção

### Métricas Atuais (2026-04-09 a 2026-04-10)
- **Chamadas realizadas:** 17
- **Taxa de conclusão (compra):** 64.7% (11 convertidas)
- **Tempo médio por chamada:** 44 segundos
- **Sem resposta (1ª tentativa):** 29.4% (retry pendente)
- **Erros técnicos:** 5.9% (investigação em curso)

---

## Ações Futuras

### Disparador Voice Agent - Abandoned Checkout
- **Otimização de horários:** Implementar janela de chamadas 9h-17h (compatibilidade GDPR + RTT)
- **Retry inteligente:** Automatizar re-tentativas para "no_answer" (agora manual)
- **A/B Testing de prompts:** Validar variações de tom e ofertas
- **Escalação de volume:** Expandir para janela 5-10 dias (potencial +300% leads/dia)
- **Integração com CRM:** Feedback de chamadas → Shopify metafields

---

## Principais Ações Implementadas

- ✅ **Cron automation fix** — Removido operador shell inválido (`\>=`), agora executa a cada 10 min
- ✅ **Phone normalization (E.164)** — Suporte a 27 países EU + extras (PT, ES, FR, EN)
- ✅ **Recording & playback** — Ultravox integration com audio proxy no dashboard /admin/calls
- ✅ **Transcrição completa** — Acesso a conversas via Ultravox API (role agent + user)
- ✅ **Call logging** — JSON persistente (`called.json`) com tracking de status e tentativas
- ✅ **Webhook integrations** — Warm transfer + log call result tools no system prompt do agente
- ✅ **Multi-language support** — PT, ES, FR, EN com VAD optimizado para codec Twilio µ-law 8kHz
- ✅ **Production deployment** — Docker Swarm VPS 144.91.85.135 com health checks

---

## Decisões Necessárias & Constrangimentos

| Decisão | Status | Impacto | Próximo Passo |
|---------|--------|--------|---------------|
| **Horário de chamadas** | ⚠️ Pendente | GDPR compliance, taxa de resposta | Definir janela 9-17h por timezone |
| **Escalação de volume** | ⚠️ Pendente | +300% leads/dia vs. custo Ultravox | Aprovação financeira (preço por min) |
| **Retry automático** | 🔧 Em progresso | 29.4% sem resposta não re-contactados | Implementar retry_date automation |
| **Warm transfer routing** | ⚪ Não utilizado | 0% transferências, posível UX issue | Testar fluxo com clientes reais |
| **Integração CRM** | ⚪ Fora de escopo | Feedback dos agentes perdido | Requerer API Shopify para metafields |

---

## Arquitetura Técnica (Resumo)

```
Shopify Checkouts (8º dia)
    ↓
Cron Job (*/10 * * * *)
    ↓
ShopifyClient.get_abandoned_checkouts()
    ↓
Phone Normalization (E.164)
    ↓
UltravoxClient.create_call()
    ↓
Twilio SIP → PSTN Call
    ↓
Voice Agent (Ultravox)
    ├─ Query Corpus (RAG Knowledge Base)
    ├─ Warm Transfer (if accepted)
    └─ Leave Voicemail (if no answer)
    ↓
Recording + Transcript logged
    ↓
Dashboard /admin/calls (audio playback + seek controls)
```

---

## Dependências & Integração

| Sistema | Endpoint | Autenticação | Status |
|---------|----------|--------------|--------|
| **Shopify API** | /checkouts.json | X-Shopify-Access-Token | ✅ Ativo |
| **Ultravox API** | /api/calls | X-API-Key | ✅ Ativo |
| **Twilio** | SIP URI | Account SID + Token | ✅ Ativo |
| **Cartesia (TTS)** | voice.cartesia.ai | API Key (opcional) | ⚠️ Fallback nativo |

---

## Ambiente & Deployment

**Produção:**
- VPS: `144.91.85.135`
- Container: `piranha-voice_piranha_voice`
- Stack: Python 3.11 + Gunicorn + Docker Swarm
- Health endpoint: `https://call.piranhasupplies.com/health`

**Logs & Monitoring:**
- Call logs: `/app/called.json` (JSON)
- System logs: `docker service logs piranha-voice_piranha_voice -f`
- Dashboard: `https://call.piranhasupplies.com/admin/calls`

---

## Roadmap (Próximos 30 dias)

| Sprint | Objetivo | Prioridade |
|--------|----------|-----------|
| **S1 (13-20 Abr)** | Retry automático + horário GDPR | 🔴 Alta |
| **S2 (21-27 Abr)** | A/B testing prompts | 🟡 Média |
| **S3 (28-04 Mai)** | Escalação para 5-10 dias | 🟡 Média |
| **S4 (05-11 Mai)** | Integração CRM + analytics | 🟢 Baixa |

---

**Última Validação:** 2026-04-13 | **Próxima Review:** 2026-04-20
