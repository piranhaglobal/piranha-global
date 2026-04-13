# Iniciativa: Scraping Leads - Estúdios de Tatuagem
**Equipa:** Marketing Digital & E-commerce  |  **Última Atualização:** 09/04/2026

---

## Indicadores & Objetivos

### Scraper de Estúdios de Tatuagem (Espanha)
- **Descrição:** Sistema de scraping multi-fonte para recolher leads de estúdios em Espanha
- **Fontes:** Google Places API + Páginas Amarillas (via Firecrawl, opcional)
- **Cobertura:** 42 cidades espanholas, 10 resultados por cidade
- **Status:** ✅ Primeiros testes realizados — coleta funcional em produção

### Dados Coletados por Lead
- Nome, morada, telefone, website, email
- Rating + total_reviews (Google Places)
- Business_status (OPERATIONAL, CLOSED_TEMPORARILY, etc.)
- Timestamp de coleta + source (google_places / paginasamarillas)

---

## Ações Futuras

### Escalação de Coleta
- Executar coleta completa em 42 cidades (atualmente apenas Madrid testado)
- Validar volume estimado: ~420 leads brutos (10/cidade)

### Deduplicação & Validação
- Implementar fuzzy matching para estúdios duplicados entre fontes
- Validar emails e telefones — testar conectividade real

### Integração CRM
- Exportar leads para Shopify metafields ou CRM externo
- Automatizar follow-up via WhatsApp ou email

### Expansão de Categorias
- Adicionar clínicas de estética / micropigmentação
- Adicionar estúdios piercing (futuros — código já preparado)

---

## Principais Ações Implementadas

- ✅ **Google Places Collector** — Text search + pagination + details API
- ✅ **Email Extractor** — Regex + mailto links + Firecrawl fallback para JS-heavy
- ✅ **Páginas Amarillas Scraper** — Parsing com Firecrawl (Docker)
- ✅ **SQLite Storage** — Upsert com deduplicação por place_id
- ✅ **CSV Export** — Relatório exportável com todos os campos
- ✅ **Rate Limiting** — Delays configuráveis (1.5s/request)
- ✅ **Error Handling** — Fallback Firecrawl + retry logic

---

## Decisões Necessárias & Constrangimentos

| Decisão | Status | Impacto | Próximo Passo |
|---------|--------|--------|---------------|
| **Google Places API Billing** | ✅ Resolvido | Custos por request — validado | Monitorar quotas |
| **Firecrawl Self-hosted** | ⚠️ Recomendado | Docker local (3002) — opcional | Instalar se JS-heavy prevalente |
| **Rate Limiting (Anti-Scraping)** | ✅ Mitigado | 1.5s delays + User-Agent browser | Aumentar delay se 429 detectado |
| **Email Validation** | ⚪ Pendente | 80% com email (4/5 amostra) | Testar conectividade SMTP |
| **Duplicação entre Fontes** | ⚪ Pendente | Google + Páginas Amarillas overlap | Implementar fuzzy matching |

---

## Arquitetura Técnica (Resumo)

```
42 Cidades (SPAIN_CITIES)
    ↓
[Coleta Paralela ou Sequencial]
    ├─ Google Places Text Search (10 results/cidade)
    │   ├─ Parse básico
    │   └─ Get Details (website + phone)
    │
    └─ Páginas Amarillas [opcional, requer Firecrawl]
        └─ HTML scraping + parsing
    ↓
Email Extractor
    ├─ Requests simples (homepage + slugs)
    ├─ Fallback Firecrawl (JS-heavy sites)
    └─ Regex + mailto: links
    ↓
SQLite Upsert (por place_id)
    ↓
CSV Export → Relatório final
```

---

## Dependências & Integração

| Sistema | Endpoint | Autenticação | Status |
|---------|----------|--------------|--------|
| **Google Places API** | maps.googleapis.com | API Key (.env) | ✅ Ativo |
| **Firecrawl (opcional)** | localhost:3002 | Health check | ⚠️ Docker |
| **Páginas Amarillas** | paginasamarillas.es | Public | ✅ Sem auth |

---

## Stack Técnico

- **Linguagem:** Python 3.8+
- **HTTP:** requests (timeout: 10s)
- **HTML Parsing:** BeautifulSoup4 + lxml
- **Database:** SQLite3 (leads.db)
- **Rendering JS:** Firecrawl (http://localhost:3002, optional)
- **Storage:** CSV export para análise

---

## Roadmap (Próximos 30 dias)

| Sprint | Objetivo | Prioridade |
|--------|----------|-----------|
| **S1 (09-16 Abr)** | Coleta completa 42 cidades | 🔴 Alta |
| **S2 (17-23 Abr)** | Deduplicação + validação | 🟡 Média |
| **S3 (24-30 Abr)** | Integração CRM / exportação | 🟡 Média |
| **S4 (01-07 Mai)** | Expansão categorias (clínicas) | 🟢 Baixa |

---

**Última Validação:** 2026-04-09 | **Próxima Review:** 2026-04-16
