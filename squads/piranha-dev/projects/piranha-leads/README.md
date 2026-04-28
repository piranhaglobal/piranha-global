# Piranha Leads

Backend Python de scraping e frontend Atlas para operar a base de leads.

## Produção

O deploy usa o Docker Swarm já existente na VPS e publica por Traefik em:

- `https://scraping.piranhasupplies.com`
- stack `piranha-leads`
- imagem local `piranha-leads:latest`
- volume persistente ` /opt/piranha-leads/data -> /app/data`

## Segurança do deploy

O fluxo de release envia apenas código para a VPS.

- `data/` não é sincronizado do portátil para a VPS
- `.env` não é sobrescrito pelo deploy
- o contexto de `docker build` também exclui `data/` e `.env`
- `deploy/setup.sh` garante que `/opt/piranha-leads/data` existe antes do rebuild

Isto evita misturar dados locais com a instância de produção.

## Atlas Research Chat

O Atlas inclui um chat operacional para transformar contexto de pesquisa em jobs de scraping.

Variáveis opcionais:

```bash
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
OPENAI_PLANNER_MODEL=gpt-5.5
ATLAS_DAILY_CHAT_CRON=1
```

Para proteger o Atlas com Google Login:

```bash
ATLAS_REQUIRE_AUTH=1
ATLAS_SESSION_SECRET=...
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://scraping.piranhasupplies.com/api/auth/google/callback
```

Quando `ATLAS_REQUIRE_AUTH=1`, o backend aceita apenas contas Google com email `@piranha.com.pt`.

Passos:

```bash
bash deploy/push-to-vps.sh
ssh root@144.91.85.135
cd /opt/piranha-leads
bash deploy/setup.sh
```
