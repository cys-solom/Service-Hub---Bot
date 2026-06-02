#!/bin/bash
# ============================================
# Auto-Deploy — runs on git push
# Called by GitHub Actions SSH or webhook
# ============================================

set -e
PROJECT_DIR="/opt/diaastore"
LOG="/var/log/diaastore-deploy.log"

echo "$(date) — Deploy triggered" >> "$LOG"

cd "$PROJECT_DIR"

# Pull latest
git fetch origin
git reset --hard origin/main

# Rebuild only changed containers
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Clean old images
docker image prune -f

echo "$(date) — Deploy complete ✅" >> "$LOG"
