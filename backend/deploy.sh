#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Deployment..."

# 1. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 2. Build and restart containers
echo "🏗️  Building and restarting containers..."
docker compose up -d --build

# 3. Prune unused images to save space
echo "🧹 Pruning unused images..."
docker image prune -f

echo "✅ Deployment Complete!"
echo "   API: http://localhost:8000"
echo "   Agent: Running in background"
