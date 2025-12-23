# Deployment Guide

This guide covers deploying the Sapphire ITSM Platform to a production host.

## Prerequisites

On your deployment host, ensure you have:
- Docker and Docker Compose installed
- Git installed
- Access to your PostgreSQL database
- Network access to required services (AI Gateway, Outline, etc.)

## Step 1: Clone the Repository

On your deployment host:

```bash
git clone https://github.com/crampedTurtle/sapphire-itsm.git
cd sapphire-itsm
```

Or if you want a specific branch/tag:
```bash
git clone -b <branch-name> https://github.com/crampedTurtle/sapphire-itsm.git
cd sapphire-itsm
```

## Step 2: Set Up Environment Variables

Create the `.env` files for each service:

```bash
# Support Core
cat > services/support-core/.env << 'EOF'
DATABASE_URL=postgresql://sapphire:YOUR_PASSWORD@YOUR_POSTGRES_HOST:5432/sapphire_support
AI_GATEWAY_URL=http://vm-ai2:8080
AI_GATEWAY_API_KEY=your_ai_key_here
OUTLINE_API_URL=https://outline.home.lan
OUTLINE_API_KEY=your_outline_key_here
APP_NAME=sapphire-support-core
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=your_generated_secret_key_here
ALLOWED_ORIGINS=https://your-portal-domain.com,https://your-ops-center-domain.com
FREESCOUT_ENABLED=false
FREESCOUT_API_URL=
FREESCOUT_API_KEY=
CRM_WEBHOOK_URL=
EOF

# Portal
cat > apps/portal/.env << 'EOF'
NEXT_PUBLIC_API_URL=https://your-api-domain.com
EOF

# Ops Center
cat > apps/ops-center/.env << 'EOF'
NEXT_PUBLIC_API_URL=https://your-api-domain.com
EOF
```

**Important:** 
- Replace `YOUR_PASSWORD` with your actual database password
- Replace `YOUR_POSTGRES_HOST` with your PostgreSQL hostname or IP
- Generate a secure `SECRET_KEY` using: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- Update `ALLOWED_ORIGINS` with your actual domain names
- Update `NEXT_PUBLIC_API_URL` with your API endpoint

## Step 3: Set Up the Database

If you haven't already set up the database:

```bash
# Connect to your PostgreSQL server
psql -U postgres -h YOUR_POSTGRES_HOST

# Run the database setup script
\i database_setup.sql
```

Or if the database and user already exist, just run the schema:
```bash
psql -U sapphire -d sapphire_support -h YOUR_POSTGRES_HOST -f database_schema_only.sql
```

## Step 4: Update Docker Compose for Production

The `docker-compose.yml` is configured for development. For production, you may want to:

1. Remove volume mounts (or keep them for logs)
2. Use production-ready images
3. Add health checks
4. Configure resource limits

You can create a `docker-compose.prod.yml` override file:

```yaml
version: '3.8'

services:
  support-core:
    restart: unless-stopped
    environment:
      APP_ENV: production
    # Remove volume mounts for production or use named volumes
    # volumes:
    #   - ./services/support-core:/app  # Remove this in production

  portal:
    restart: unless-stopped
    # Remove volume mounts for production
    # volumes:
    #   - ./apps/portal:/app

  ops-center:
    restart: unless-stopped
    # Remove volume mounts for production
    # volumes:
    #   - ./apps/ops-center:/app
```

Then use: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Step 5: Build and Start Services

```bash
# Build the images
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 6: Run Database Migrations

```bash
docker-compose exec support-core alembic upgrade head
```

## Step 7: Verify Deployment

Check that all services are running:

```bash
docker-compose ps
```

Test the endpoints:
- API Health: `curl http://localhost:8000/docs` (or your API domain)
- Portal: Open in browser at configured port
- Ops Center: Open in browser at configured port

## Production Considerations

### Reverse Proxy Setup

For production, you'll likely want to use a reverse proxy (nginx, Traefik, etc.) to:
- Handle SSL/TLS termination
- Route traffic to the correct services
- Handle domain names

Example nginx configuration:

```nginx
# API
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Portal
server {
    listen 443 ssl;
    server_name portal.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Ops Center
server {
    listen 443 ssl;
    server_name ops.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Updating the Deployment

To update to the latest code:

```bash
# Pull latest changes
git pull origin main  # or your branch name

# Rebuild and restart
docker-compose build
docker-compose up -d

# Run any new migrations
docker-compose exec support-core alembic upgrade head
```

### Monitoring and Logs

```bash
# View logs
docker-compose logs -f support-core
docker-compose logs -f portal
docker-compose logs -f ops-center

# Check resource usage
docker stats
```

### Backup

Make sure to regularly backup your PostgreSQL database:

```bash
pg_dump -h YOUR_POSTGRES_HOST -U sapphire -d sapphire_support > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Database Connection Issues

If containers can't reach your PostgreSQL:
- Ensure PostgreSQL allows connections from Docker network
- Check firewall rules
- Verify DATABASE_URL in `.env` file
- Test connection: `docker-compose exec support-core psql $DATABASE_URL`

### Port Conflicts

If ports are already in use, update `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change external port
```

### Container Won't Start

Check logs:
```bash
docker-compose logs support-core
```

Common issues:
- Missing environment variables
- Database not accessible
- Port conflicts

## Quick Deploy Script

You can create a deploy script:

```bash
#!/bin/bash
# deploy.sh

set -e

echo "Pulling latest code..."
git pull

echo "Building images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo "Running migrations..."
docker-compose exec -T support-core alembic upgrade head

echo "Deployment complete!"
docker-compose ps
```

Make it executable: `chmod +x deploy.sh`
Run it: `./deploy.sh`

