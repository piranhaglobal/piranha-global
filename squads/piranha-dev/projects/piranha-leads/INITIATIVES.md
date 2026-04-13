# Iniciativa: Scraping Leads - Estúdios de Tatuagem
**Equipa:** Marketing Digital & E-commerce  |  **Última Atualização:** 09/04/2026

---

## Indicadores & Objetivos

### Scraper de Leads - Estúdios de Tatuagem (Espanha)
- **Sistema de scraping multi-fonte para recolher leads de estúdios em Espanha via Google Places + Páginas Amarillas**
- **Um momento de coleta: execução via Google Places API (10 leads/cidade × 42 cidades = ~420 leads potenciais)**
- **Status: Primeiros testes realizados — 5 leads Madrid validados, estrutura estável, coleta funcional**

---

## Ações Futuras

### Scraper de Leads - Estúdios de Tatuagem
- **Sistema estável — coleta completa 42 cidades + deduplicação em progresso**

---

## Principais Ações Implementadas

### Scraper de Leads - Estúdios de Tatuagem
- **Coleta Google Places operacional (text search + pagination + details), multilingue (ES), deduplicada por place_id, deployed e a gerar leads.csv em /data**
- **Coleta Páginas Amarillas (Firecrawl Docker, optional) + email extractor (regex + mailto + Firecrawl fallback para JS-heavy)**
- **SQLite storage (upsert), CSV export, rate limiting (1.5s/req), error handling com retry logic**
- **5 leads Madrid (80% com email, 100% com telefone + website, rating médio 4.82/5)**

---

## Decisões Necessárias & Constrangimentos

- **Google Places API Billing resolvido — quotas em monitoração**

---

**Última Validação:** 2026-04-09 | **Próxima Review:** 2026-04-16
