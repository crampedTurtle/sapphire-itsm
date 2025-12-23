# Sapphire Support Core

FastAPI service providing the decision plane and system of record for customer operations.

## Features

- Email and portal intake normalization
- Tenant resolution and entitlement
- AI intent classification
- Case lifecycle management
- SLA tracking
- Audit logging
- CRM sync events
- Knowledge retrieval hooks (Outline)
- **Onboarding & Tier Lifecycle Management** (NEW)

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

## Environment Variables

See `.env.example` for required configuration.

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run server
uvicorn app.main:app --reload
```

## Testing

```bash
pytest
```

## Onboarding & Tier Lifecycle API

The Support Core provides a first-class, idempotent Onboarding & Tier Lifecycle API that integrates with Supabase → n8n orchestration and feeds the Ops Center.

### Supabase → n8n → Support Core Flow

1. **Supabase detects new tenant registration**
2. **n8n workflow triggers** and calls `POST /v1/onboarding/start`
3. **Support Core creates**:
   - Tenant record (if not exists)
   - Onboarding session
   - Initial onboarding steps (Phase 0)
   - SLA policy
   - Tenant entitlements
4. **Ops Center immediately sees** new tenant with onboarding status

### Onboarding Lifecycle

#### Phases

1. **Phase 0: Provisioned** - Infrastructure ready
   - AWS environment provisioned
   - Supabase database ready

2. **Phase 1: First Value** - Initial engagement
   - Portal login
   - First AI question asked
   - Knowledge base search

3. **Phase 2: Core Workflows** - Active usage
   - First support case created
   - Case resolved
   - Email intake received

4. **Phase 3: Independent** - Self-sufficient
   - Multiple cases handled
   - Self-service success
   - Team adoption

#### State Machine

```
not_started → phase_0_provisioned → phase_1_first_value → 
phase_2_core_workflows → phase_3_independent → completed
```

States: `active`, `paused`, `completed`, `failed`

### API Endpoints

#### Start Onboarding

```bash
POST /v1/onboarding/start
{
  "tenant_id": "uuid",
  "tenant_name": "Smith & Cole LLP",
  "primary_domain": "smithcolelaw.com",
  "plan_tier": "tier1",
  "trigger_source": "supabase_registration"
}
```

**Idempotent**: Returns existing session if already started.

#### Get Onboarding Status

```bash
GET /v1/onboarding/status/{tenant_id}
```

Returns current phase, status, and step completion.

#### Advance Step

```bash
POST /v1/onboarding/advance-step
{
  "tenant_id": "uuid",
  "step_key": "first_ai_question",
  "metadata": {"confidence": 0.82}
}
```

Automatically advances phase when all steps complete.

#### Pause/Resume

```bash
POST /v1/onboarding/pause
POST /v1/onboarding/resume
{
  "tenant_id": "uuid",
  "reason": "Customer requested delay"
}
```

#### Complete Onboarding

```bash
POST /v1/onboarding/complete
{
  "tenant_id": "uuid"
}
```

Called automatically when Phase 3 completes.

#### Tier Upgrade/Downgrade

```bash
POST /v1/onboarding/upgrade
{
  "tenant_id": "uuid",
  "previous_tier": "tier1",
  "new_tier": "tier2",
  "trigger_source": "supabase_change"
}
```

Updates entitlements, SLA policy, and feature flags.

### Tier Entitlement Mapping

| Tier | Portal | FreeScout | AI Features |
|------|--------|-----------|-------------|
| Tier 0 | ✅ | ❌ | Intent classification only |
| Tier 1 | ✅ | ✅ | + KB RAG, Draft replies |
| Tier 2 | ✅ | ✅ | Full AI features |

### Ops Center Integration

New tenants appear immediately in Ops Center with:
- `status: "onboarding"`
- `onboarding.phase`: Current phase
- `onboarding.is_onboarding: true`
- SLA timers paused during onboarding

Onboarding friction surfaced as:
- Repeated step failures
- Tier 1 cases during onboarding
- Phase advancement delays

### Guardrails

- **All endpoints are idempotent** - Safe to retry
- **No side effects** - No email, AWS, or Supabase modifications
- **Everything auditable** - All state transitions create audit events
- **Support Core owns truth** - Supabase is not authoritative for onboarding state

