# Relatório de Dados — Piranha Leads
**Período:** Março–Abril 2026

---

## Dados Recolhidos

### Resumo Quantitativo
- **Total de leads no sistema:** 5 estúdios
- **Cidades cobertas:** 1 (Madrid)
- **Fontes de dados:** Google Places (100%)
- **Período de coleta:** 09/04/2026, 11:46–11:47

### Campos Disponíveis
| Campo | Completude | Observações |
|-------|-----------|-------------|
| **Nome** | 100% (5/5) | Rastreável, sem duplicados por place_id |
| **Morada** | 100% (5/5) | Formato: "Rua, número, bairro, código postal, cidade" |
| **Telefone** | 100% (5/5) | Formato: +34 (prefixo Espanha) |
| **Website** | 100% (5/5) | URLs válidas e acessíveis |
| **Email** | 80% (4/5) | 1 sem email extraído |
| **Rating** | 100% (5/5) | Escala 0–5 (mínimo 4.7, máximo 4.9) |
| **Reviews** | 100% (5/5) | Volume: 531–4234 avaliações |

### Amostra de Registos (3 primeiros)

| ID | Nome | Cidade | Email | Telefone | Rating | Reviews |
|----|------|--------|-------|----------|--------|---------|
| 1 | 222 Tattoo Madrid | Madrid | info@222tattoomadrid.com | +34 626 37 30 74 | 4.9 | 4234 |
| 2 | Ink Sweet Tattoo Studio | Madrid | tatuate@inksweettattoo.es | +34 640 31 31 04 | 4.9 | 531 |
| 3 | La Manuela Tattoo | Madrid | — | +34 915 46 17 52 | 4.8 | 904 |

---

## Observações & Qualidade

### Estado dos Dados
- ✅ **Primeiros testes realizados** — 5 leads validados manualmente
- ✅ **Estrutura estável** — esquema SQLite consolidado
- ✅ **Sem duplicados** — place_id garante unicidade por Google Place

### Padrões Identificados
- **Rating elevado:** Média 4.82/5 (indicador de estúdios de qualidade)
- **Volume review elevado:** Média 1.645 avaliações (estúdios estabelecidos)
- **Cobertura email:** 80% — compatível com automação CRM
- **Status operacional:** 100% OPERATIONAL — nenhum fechado temporariamente

### Próximas Etapas para Validação
1. Executar coleta completa (42 cidades) — estimado 420 leads brutos
2. Testar conectividade de telefones (SMS) e emails (SMTP)
3. Identificar e remover duplicados entre Google Places + Páginas Amarillas
4. Validar cobertura geográfica vs. diretório público de referência

---

**Data de Geração:** 2026-04-09  
**Fonte de Dados:** SQLite (`/data/leads.db`) + CSV export (`/data/leads.csv`)  
**Próxima Atualização:** Após coleta completa (42 cidades)
