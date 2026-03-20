#!/bin/bash
# ============================================================
# Envia o projeto piranha-supplies-voice para a VPS.
# Executar no teu computador: bash deploy/push-to-vps.sh
# ============================================================

set -e

VPS_IP="144.91.85.135"
VPS_USER="root"
REMOTE_DIR="/opt/piranha-supplies-voice"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "A enviar $LOCAL_DIR → $VPS_USER@$VPS_IP:$REMOTE_DIR"

rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'venv/' \
  --exclude 'called.json' \
  "$LOCAL_DIR/" "$VPS_USER@$VPS_IP:$REMOTE_DIR/"

echo ""
echo "Transferência concluída."
echo ""
echo "Próximo passo — correr na VPS:"
echo "  ssh $VPS_USER@$VPS_IP"
echo "  cd $REMOTE_DIR && bash deploy/setup.sh"
