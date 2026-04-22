# Piranha Leads

Backend Python de scraping e frontend Atlas para operar a base de leads.

## Produção

O deploy usa o Docker Swarm já existente na VPS e publica por Traefik em:

- `https://scraping.piranhasupplies.com`
- stack `piranha-leads`
- imagem local `piranha-leads:latest`
- volume persistente ` /opt/piranha-leads/data -> /app/data`

Passos:

```bash
bash deploy/push-to-vps.sh
ssh root@144.91.85.135
cd /opt/piranha-leads
bash deploy/setup.sh
```
