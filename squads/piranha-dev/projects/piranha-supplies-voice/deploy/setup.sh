#!/bin/bash
# ============================================================
# Piranha Supplies Voice — Deploy em Docker Swarm
# Executar na VPS como root: bash deploy/setup.sh
# ============================================================

set -e

PROJECT_DIR="/opt/piranha-supplies-voice"
IMAGE_NAME="piranha-voice:latest"
STACK_NAME="piranha-voice"

echo "=== [1/3] Build da imagem Docker ==="
cd "$PROJECT_DIR"
docker build -t "$IMAGE_NAME" .
echo "Imagem $IMAGE_NAME criada."

echo ""
echo "=== [2/3] Deploy no Swarm ==="
docker stack deploy -c deploy/piranha-voice-stack.yml "$STACK_NAME" --with-registry-auth
echo "Stack '$STACK_NAME' deployada."

echo ""
echo "=== [3/3] Verificar serviço ==="
sleep 5
docker service ls | grep piranha

echo ""
echo "================================================"
echo "Deploy concluído!"
echo ""
echo "Endpoints:"
echo "  https://call.piranhasupplies.com/webhook/twilio/twiml"
echo "  https://call.piranhasupplies.com/webhook/twilio/status"
echo "  https://call.piranhasupplies.com/health"
echo ""
echo "Comandos úteis:"
echo "  docker service ls                              — ver todos os serviços"
echo "  docker service logs piranha-voice_piranha_voice -f  — logs em tempo real"
echo "  docker service ps piranha-voice_piranha_voice  — estado do container"
echo "  bash deploy/setup.sh                           — redeploy"
echo "================================================"
