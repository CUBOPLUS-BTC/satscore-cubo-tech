#!/bin/bash
# Deploy Magma backend on Hetzner - Docker + Postgres
set -e

echo "=== Magma Backend Deployment ==="

cd /opt/magma

# Pull latest code
git pull origin main

# Rebuild and restart containers
echo "Building and starting containers..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "=== Deployment complete ==="
docker compose -f docker-compose.prod.yml ps
echo ""
echo "Logs: docker compose -f docker-compose.prod.yml logs -f backend"
