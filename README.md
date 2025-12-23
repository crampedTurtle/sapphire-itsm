# Sapphire Customer Ops Platform

Production-ready, portal-first customer operations platform for Sapphire Legal AI. The platform treats **emails as an input channel** and **cases as structured decisions**.

## Architecture

The platform consists of three core services:

1. **sapphire-support-core** - FastAPI service (Decision Plane + System of Record)
2. **sapphire-portal** - Next.js customer portal (Tier 0/1/2)
3. **sapphire-ops-center** - Next.js internal ops dashboard

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)
- Node.js 18+ (for local development without Docker)

### Setup

1. Clone the repository and navigate to the root directory.

2. Copy environment files:
   ```bash
   cp services/support-core/.env.example services/support-core/.env
   cp apps/portal/.env.example apps/portal/.env
   cp apps/ops-center/.env.example apps/ops-center/.env
   ```

3. Update `.env` files with your configuration:
   - Postgres connection: `postgres.home.lan` (or override with env vars)
   - AI gateway endpoint: `http://vm-ai2:8080` (or your AI service)
   - Outline API: `https://outline.home.lan` (or your Outline instance)
   - Mailcow SMTP settings (for n8n integration)

4. Start all services:
   ```bash
   make dev
   # or
   docker-compose up -d
   ```

5. Run database migrations:
   ```bash
   make migrate
   # or
   docker-compose exec support-core alembic upgrade head
   ```

6. Access the services:
   - Portal: http://localhost:3000
   - Ops Center: http://localhost:3001
   - Support Core API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Development

### Running Tests

```bash
make test
# or
docker-compose exec support-core pytest
```

### Database Migrations

Create a new migration:
```bash
docker-compose exec support-core alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
make migrate
```

## Integration Guide

### n8n Integration

n8n orchestrates email intake and outbound email. Configure n8n workflows to:

1. **Email Intake**: Read emails from Mailcow IMAP and call:
   ```
   POST http://support-core:8000/v1/intake/email
   Content-Type: application/json
   
   {
     "from_email": "customer@example.com",
     "to_email": "support@sapphire.ai",
     "subject": "Help with feature X",
     "body_text": "I need help...",
     "raw_payload": {...}
   }
   ```

2. **Outbound Email**: Use Mailcow SMTP through n8n to send responses. Support-core will return webhook payloads with email templates.

3. **FreeScout Sync** (optional): Call `/v1/webhooks/freescout/sync` when creating/updating cases.

### Outline Integration

Configure Outline connection in `support-core/.env`:
```
OUTLINE_API_URL=https://outline.home.lan
OUTLINE_API_KEY=your_api_key
```

The KB adapter searches Outline content and retrieves relevant pages for Tier 0 self-service responses.

### AI Gateway Integration

Configure AI endpoint in `support-core/.env`:
```
AI_GATEWAY_URL=http://vm-ai2:8080
AI_GATEWAY_API_KEY=your_key_if_needed
```

The AI client abstraction supports:
- Intent classification
- Response generation
- KB answer with citations (RAG)

### Postgres Configuration

Default connection: `postgres.home.lan:5432`

Override in `support-core/.env`:
```
DATABASE_URL=postgresql://user:pass@postgres.home.lan:5432/sapphire_support
```

## Service Details

### Support Core API

FastAPI service providing:
- Intake normalization (email + portal)
- Tenant resolution + entitlement
- AI intent classification
- Case lifecycle management
- SLA tracking
- Audit logging
- CRM sync events
- Knowledge retrieval hooks

See `services/support-core/README.md` for detailed API documentation.

### Portal

Next.js customer portal with:
- Tier 0: Self-service KB search and AI answers
- Tier 1/2: Case creation, status tracking, thread replies

### Ops Center

Next.js internal dashboard with:
- Intake metrics and intent distribution
- Case queue management
- SLA risk monitoring
- Compliance flags
- AI confidence alerts

## Security & Compliance

- All AI artifacts are auditable with model, timestamp, and input references
- Global "no hallucinations" rule: draft responses acknowledge uncertainty
- Never provides legal advice; operational guidance only
- All case actions are logged in audit_events

## Project Structure

```
sapphire-itsm/
├── services/
│   └── support-core/          # FastAPI decision plane + system of record
│       ├── app/
│       │   ├── api/v1/         # API endpoints
│       │   ├── models/         # SQLAlchemy models
│       │   ├── services/       # Business logic
│       │   └── core/           # Config, database
│       ├── alembic/            # Database migrations
│       └── tests/              # Unit tests
├── apps/
│   ├── portal/                # Next.js customer portal
│   └── ops-center/            # Next.js ops dashboard
├── docker-compose.yml         # Local development setup
└── Makefile                   # Convenience commands
```

## Key Workflows

### Email Intake Flow

1. n8n reads email from Mailcow IMAP
2. n8n calls `POST /v1/intake/email` on support-core
3. support-core resolves tenant by domain
4. AI classifies intent (sales/support/etc.)
5. Routes based on intent and tier:
   - Sales → CRM event + acknowledgment email
   - Support Tier 0 → KB answer + self-service response
   - Support Tier 1/2 → Create case + AI summary + draft response

### Portal Self-Service Flow

1. Customer asks question in portal
2. Portal calls `POST /v1/portal/ask`
3. support-core searches Outline KB
4. AI generates RAG answer with citations
5. Portal displays answer with source links

### Case Management Flow

1. Customer creates case via portal (Tier 1/2 only)
2. support-core creates case, generates AI summary
3. Customer can view status and reply in thread
4. Ops Center monitors queue, updates priority/status
5. SLA tracking monitors breaches

## Testing

Run unit tests:
```bash
make test
```

Tests cover:
- Tenant resolution
- Intent routing decisions
- Case creation
- Audit logging

## License

Proprietary - Sapphire Legal AI

