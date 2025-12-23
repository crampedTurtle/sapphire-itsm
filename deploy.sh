#!/bin/bash
# Quick deployment script for Sapphire ITSM Platform

set -e

echo "🚀 Deploying Sapphire ITSM Platform..."

# Check if .env files exist
if [ ! -f "services/support-core/.env" ]; then
    echo "❌ Error: services/support-core/.env not found"
    echo "Please create the .env files first (see DEPLOYMENT.md)"
    exit 1
fi

# Pull latest code (if in git repo)
if [ -d ".git" ]; then
    echo "📥 Pulling latest code..."
    git pull || echo "⚠️  Git pull failed, continuing with current code..."
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo "▶️  Starting services..."
docker-compose up -d

# Wait for support-core to be ready
echo "⏳ Waiting for support-core to start..."
sleep 5

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T support-core alembic upgrade head || echo "⚠️  Migration failed, check logs"

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service status:"
docker-compose ps
echo ""
echo "📊 View logs with: docker-compose logs -f"
echo "🌐 Services should be available at:"
echo "   - Portal: http://localhost:3000"
echo "   - Ops Center: http://localhost:3001"
echo "   - API Docs: http://localhost:8000/docs"

