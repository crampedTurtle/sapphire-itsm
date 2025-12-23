# Database Setup Guide

This guide explains how to set up the PostgreSQL database for the Sapphire ITSM Platform.

## Prerequisites

- PostgreSQL 13+ (for `gen_random_uuid()` support)
- Access to PostgreSQL as a superuser (typically `postgres` user)

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the complete setup script:

```bash
psql -U postgres -f database_setup.sql
```

This will:
1. Create the `sapphire_support` database
2. Create the `sapphire` user with password `sapphire`
3. Create all enums
4. Create all tables with indexes and constraints
5. Set up triggers for `updated_at` timestamps
6. Grant all necessary permissions

### Option 2: Manual Setup

If you prefer to run steps separately:

1. **Create database and user:**
   ```bash
   psql -U postgres -f database_create_user.sql
   ```

2. **Create schema (connect to database first):**
   ```bash
   psql -U postgres -d sapphire_support -f database_setup.sql
   ```
   (Note: You may need to comment out the database/user creation section if running this way)

## Database Connection

After setup, the application connects using:

```
postgresql://sapphire:sapphire@localhost:5432/sapphire_support
```

Or override with environment variable:
```bash
DATABASE_URL=postgresql://sapphire:sapphire@postgres.home.lan:5432/sapphire_support
```

## Production Considerations

⚠️ **IMPORTANT**: Change the default password in production!

1. Generate a strong password
2. Update the password:
   ```sql
   ALTER USER sapphire WITH PASSWORD 'your_secure_password_here';
   ```
3. Update your `.env` file with the new password

## Using Docker Compose

If you're using Docker Compose, the database is automatically created with these credentials:
- Database: `sapphire_support`
- User: `sapphire`
- Password: `sapphire`

The migrations will run automatically when the `support-core` service starts.

## Manual Migration (Alternative to SQL Scripts)

If you prefer to use Alembic migrations instead of the SQL scripts:

```bash
# From the services/support-core directory
docker-compose exec support-core alembic upgrade head
# or
cd services/support-core
alembic upgrade head
```

## Database Schema Overview

The database includes the following main tables:

- **tenants** - Customer organizations
- **identities** - Users (customers, agents, ops)
- **intake_events** - Email/portal intake records
- **intent_classifications** - AI intent analysis results
- **cases** - Support cases
- **case_messages** - Case thread messages
- **ai_artifacts** - AI-generated summaries and responses
- **sla_policies** - SLA definitions per tier
- **sla_events** - SLA tracking events
- **audit_events** - Audit trail
- **crm_events** - CRM integration events
- **onboarding_sessions** - Customer onboarding tracking
- **onboarding_steps** - Onboarding step completion
- **tenant_entitlements** - Feature entitlements per tenant

## Troubleshooting

### UUID Generation Error

If you see an error about `gen_random_uuid()`, you may need to enable the extension:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

### Permission Errors

If you encounter permission errors, ensure you're running as the postgres superuser for initial setup, or ensure the `sapphire` user has been granted proper permissions.

### Connection Refused

- Verify PostgreSQL is running: `pg_isready`
- Check the connection string matches your PostgreSQL host/port
- Verify firewall rules allow connections

