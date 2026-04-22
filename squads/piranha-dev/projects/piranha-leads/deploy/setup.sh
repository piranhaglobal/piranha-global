#!/bin/bash

set -euo pipefail

PROJECT_DIR="/opt/piranha-leads"
IMAGE_NAME="piranha-leads:latest"
STACK_NAME="piranha-leads"

echo "=== [1/4] Docker build ==="
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/data"
docker build -t "$IMAGE_NAME" .

echo ""
echo "=== [2/4] Docker Swarm deploy ==="
docker stack deploy -c deploy/piranha-leads-stack.yml "$STACK_NAME" --with-registry-auth
docker service update --force "${STACK_NAME}_piranha_leads" >/dev/null

echo ""
echo "=== [3/4] Verificar serviço ==="
sleep 5
docker service ls | grep piranha-leads || true
docker service ps piranha-leads_piranha_leads --no-trunc || true

echo ""
echo "=== [4/4] Smoke test ==="
curl -I https://scraping.piranhasupplies.com || true

echo ""
echo "Deploy concluído."
echo "Frontend + API: https://scraping.piranhasupplies.com"
