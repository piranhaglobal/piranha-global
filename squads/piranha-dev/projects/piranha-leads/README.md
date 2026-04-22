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

Passos:

```bash
bash deploy/push-to-vps.sh
ssh root@144.91.85.135
cd /opt/piranha-leads
bash deploy/setup.sh
```
