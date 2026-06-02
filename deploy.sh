#!/bin/bash
# ============================================
# Diaa Store — Server Setup & Deploy Script
# Run: chmod +x deploy.sh && ./deploy.sh
# ============================================

set -e

PROJECT_DIR="/opt/diaastore"
REPO_URL="GITHUB_REPO_URL_HERE"  # Change this!
BRANCH="main"

echo "🚀 Diaa Store — Deployment Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Install Docker (if not installed) ──
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose installed"
fi

# ── Step 2: Clone or pull repo ──
if [ -d "$PROJECT_DIR" ]; then
    echo "📥 Pulling latest changes..."
    cd "$PROJECT_DIR"
    git fetch origin
    git reset --hard origin/$BRANCH
else
    echo "📦 Cloning repository..."
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown $USER:$USER "$PROJECT_DIR"
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# ── Step 3: Check .env exists ──
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "   Copy .env.example and configure:"
    echo "   cp .env.example .env && nano .env"
    exit 1
fi

# ── Step 4: Build & Deploy ──
echo "🔨 Building containers..."
docker compose -f docker-compose.prod.yml build --no-cache

echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment Complete!"
echo ""
echo "🌐 Admin Panel: http://$(hostname -I | awk '{print $1}'):80"
echo "🔌 Backend API: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "📋 Useful commands:"
echo "   docker compose -f docker-compose.prod.yml logs -f        # View logs"
echo "   docker compose -f docker-compose.prod.yml restart bot     # Restart bot"
echo "   docker compose -f docker-compose.prod.yml down            # Stop all"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
