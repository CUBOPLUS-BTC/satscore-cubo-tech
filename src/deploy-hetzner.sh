#!/bin/bash
# Deploy script for Hetzner Cloud - Run this on your Hetzner server

set -e

# Configuration
IMAGE_NAME="satsscore-backend"
CONTAINER_NAME="satsscore_backend"
PORT=8000

echo "=== SatsScore Backend Deployment ==="

# Navigate to app directory
cd /app

# Pull latest code (if using git)
# git pull origin main

# Build the image
echo "Building Docker image..."
docker build -t $IMAGE_NAME:latest -f Dockerfile .

# Stop existing container
echo "Stopping existing container..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Run new container
echo "Starting new container..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart always \
  --env-file .env.production \
  -p $PORT:8000 \
  -v $(pwd)/satsscore.db:/app/satsscore.db \
  $IMAGE_NAME:latest

echo "=== Deployment complete ==="
echo "Backend running on port $PORT"
docker ps | grep $CONTAINER_NAME
