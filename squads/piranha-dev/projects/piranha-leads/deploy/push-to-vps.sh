#!/bin/bash

set -euo pipefail

VPS_IP="144.91.85.135"
VPS_USER="root"
REMOTE_DIR="/opt/piranha-leads"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "A enviar $LOCAL_DIR -> $VPS_USER@$VPS_IP:$REMOTE_DIR"

rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv/' \
  --exclude 'atlas/node_modules/' \
  --exclude 'atlas/dist/' \
  "$LOCAL_DIR/" "$VPS_USER@$VPS_IP:$REMOTE_DIR/"

echo ""
echo "Transferência concluída."
echo "Próximo passo:"
echo "  ssh $VPS_USER@$VPS_IP"
echo "  cd $REMOTE_DIR && bash deploy/setup.sh"
