#!/bin/bash

# Rebuild Cognito containers from scratch
# This script stops, removes, and rebuilds both backend and frontend containers

set -e  # Exit on any error

echo "🔄 Rebuilding Cognito containers from scratch..."

# Backend
echo ""
echo "📦 Rebuilding backend..."
cd backend
docker compose down
docker compose build --no-cache
docker compose up -d
cd ..

# Frontend
echo ""
echo "📦 Rebuilding frontend..."
cd frontend
docker compose down
docker compose build --no-cache
docker compose up -d
cd ..

echo ""
echo "✅ All containers rebuilt successfully!"
echo ""
echo "Container status:"
docker ps --filter "name=cognito-"
