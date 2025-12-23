-- ============================================================================
-- Sapphire ITSM Platform - Database Setup Script
-- ============================================================================
-- This script creates the database, user, enums, and all tables needed for
-- the Sapphire Customer Ops Platform.
--
-- Usage:
--   psql -U postgres -f database_setup.sql
--
-- Note: Change the password in production!
-- ============================================================================

-- ============================================================================
-- 1. CREATE DATABASE AND USER
-- ============================================================================
-- Note: Run this section as postgres superuser
-- If database/user already exist, you can skip to section 2

-- Create database (will error if exists - that's okay)
CREATE DATABASE sapphire_support;

-- Create user (will error if exists - that's okay)
CREATE USER sapphire WITH PASSWORD 'sapphire';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sapphire_support TO sapphire;

-- Connect to the database
\c sapphire_support

-- Enable UUID extension (for gen_random_uuid() if needed)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO sapphire;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sapphire;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO sapphire;

-- ============================================================================
-- 2. CREATE ENUMS
-- ============================================================================

-- Plan Tier Enum
CREATE TYPE plantier AS ENUM ('tier0', 'tier1', 'tier2');

-- Identity Role Enum
CREATE TYPE identityrole AS ENUM ('customer', 'agent', 'ops');

-- Intake Source Enum
CREATE TYPE intakesource AS ENUM ('email', 'portal');

-- Intent Enum
CREATE TYPE intent AS ENUM ('sales', 'support', 'onboarding', 'billing', 'compliance', 'outage', 'unknown');

-- Urgency Enum
CREATE TYPE urgency AS ENUM ('low', 'normal', 'high', 'critical');

-- Recommended Action Enum
CREATE TYPE recommendedaction AS ENUM ('self_service', 'create_case', 'route_sales', 'escalate_ops', 'needs_review');

-- Case Status Enum
CREATE TYPE casestatus AS ENUM ('new', 'open', 'pending_customer', 'pending_internal', 'escalated', 'resolved', 'closed');

-- Case Priority Enum
CREATE TYPE casepriority AS ENUM ('low', 'normal', 'high', 'critical');

-- Case Category Enum
CREATE TYPE casecategory AS ENUM ('support', 'onboarding', 'billing', 'compliance', 'outage');

-- Sender Type Enum
CREATE TYPE sendertype AS ENUM ('customer', 'agent', 'system');

-- Artifact Type Enum
CREATE TYPE artifacttype AS ENUM ('summary', 'draft_reply', 'kb_answer');

-- SLA Event Type Enum
CREATE TYPE slaeventtype AS ENUM ('started', 'first_response', 'breached_first_response', 'breached_resolution', 'paused', 'resumed');

-- Onboarding Phase Enum
CREATE TYPE onboardingphase AS ENUM ('not_started', 'phase_0_provisioned', 'phase_1_first_value', 'phase_2_core_workflows', 'phase_3_independent', 'completed', 'paused', 'failed');

-- Onboarding Status Enum
CREATE TYPE onboardingstatus AS ENUM ('active', 'paused', 'completed', 'failed');

-- Onboarding Trigger Enum
CREATE TYPE onboardingtrigger AS ENUM ('supabase_registration', 'tier_upgrade', 'manual_restart');

-- ============================================================================
-- 3. CREATE TABLES
-- ============================================================================

-- Tenants Table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    primary_domain VARCHAR UNIQUE,
    plan_tier plantier NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tenants_primary_domain ON tenants(primary_domain);

-- Identities Table
CREATE TABLE identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR NOT NULL,
    display_name VARCHAR,
    role identityrole NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_identities_email ON identities(email);
CREATE INDEX idx_identities_tenant_id ON identities(tenant_id);

-- Intake Events Table
CREATE TABLE intake_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source intakesource NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    from_email VARCHAR NOT NULL,
    subject VARCHAR,
    body_text TEXT NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_intake_events_tenant_id ON intake_events(tenant_id);
CREATE INDEX idx_intake_events_from_email ON intake_events(from_email);
CREATE INDEX idx_intake_events_created_at ON intake_events(created_at);

-- Intent Classifications Table
CREATE TABLE intent_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_event_id UUID NOT NULL REFERENCES intake_events(id),
    intent intent NOT NULL,
    urgency urgency NOT NULL,
    confidence FLOAT NOT NULL,
    compliance_flag BOOLEAN NOT NULL,
    recommended_action recommendedaction NOT NULL,
    model_used VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_intent_classifications_intake_event_id ON intent_classifications(intake_event_id);

-- Cases Table
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    external_source VARCHAR,
    external_case_id VARCHAR,
    title VARCHAR NOT NULL,
    status casestatus NOT NULL,
    priority casepriority NOT NULL,
    category casecategory NOT NULL,
    created_by_identity_id UUID REFERENCES identities(id),
    owner_identity_id UUID REFERENCES identities(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_tenant_id ON cases(tenant_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_owner_identity_id ON cases(owner_identity_id);
CREATE INDEX idx_cases_created_at ON cases(created_at);

-- Case Messages Table
CREATE TABLE case_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id),
    sender_type sendertype NOT NULL,
    sender_email VARCHAR NOT NULL,
    body_text TEXT NOT NULL,
    attachments JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_case_messages_case_id ON case_messages(case_id);
CREATE INDEX idx_case_messages_created_at ON case_messages(created_at);

-- AI Artifacts Table
CREATE TABLE ai_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    intake_event_id UUID REFERENCES intake_events(id),
    artifact_type artifacttype NOT NULL,
    content TEXT NOT NULL,
    citations JSONB,
    confidence FLOAT,
    model_used VARCHAR NOT NULL,
    prompt_metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_artifacts_case_id ON ai_artifacts(case_id);
CREATE INDEX idx_ai_artifacts_intake_event_id ON ai_artifacts(intake_event_id);

-- SLA Policies Table
CREATE TABLE sla_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    tier plantier NOT NULL,
    first_response_minutes INTEGER NOT NULL,
    resolution_minutes INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sla_policies_tenant_id ON sla_policies(tenant_id);

-- SLA Events Table
CREATE TABLE sla_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id),
    event_type slaeventtype NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sla_events_case_id ON sla_events(case_id);
CREATE INDEX idx_sla_events_created_at ON sla_events(created_at);

-- Audit Events Table
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    intake_event_id UUID REFERENCES intake_events(id),
    event_type VARCHAR NOT NULL,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_events_case_id ON audit_events(case_id);
CREATE INDEX idx_audit_events_intake_event_id ON audit_events(intake_event_id);
CREATE INDEX idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_created_at ON audit_events(created_at);

-- CRM Events Table
CREATE TABLE crm_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    event_type VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crm_events_tenant_id ON crm_events(tenant_id);
CREATE INDEX idx_crm_events_event_type ON crm_events(event_type);
CREATE INDEX idx_crm_events_created_at ON crm_events(created_at);

-- Onboarding Sessions Table
CREATE TABLE onboarding_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id),
    current_phase onboardingphase NOT NULL,
    status onboardingstatus NOT NULL,
    trigger_source onboardingtrigger NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_onboarding_sessions_tenant_id ON onboarding_sessions(tenant_id);

-- Onboarding Steps Table
CREATE TABLE onboarding_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    onboarding_session_id UUID NOT NULL REFERENCES onboarding_sessions(id),
    phase onboardingphase NOT NULL,
    step_key VARCHAR NOT NULL,
    step_label VARCHAR NOT NULL,
    completed BOOLEAN NOT NULL,
    completed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_onboarding_steps_onboarding_session_id ON onboarding_steps(onboarding_session_id);

-- Tenant Entitlements Table
CREATE TABLE tenant_entitlements (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
    plan_tier VARCHAR NOT NULL,
    sla_policy_id UUID REFERENCES sla_policies(id),
    portal_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    freescout_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ai_features JSONB,
    effective_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. CREATE TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to cases table
CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to tenant_entitlements table
CREATE TRIGGER update_tenant_entitlements_updated_at BEFORE UPDATE ON tenant_entitlements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to onboarding_sessions table
CREATE TRIGGER update_onboarding_sessions_last_updated_at BEFORE UPDATE ON onboarding_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. GRANT PERMISSIONS
-- ============================================================================

-- Grant all privileges on all tables to sapphire user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sapphire;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sapphire;

-- ============================================================================
-- Setup Complete!
-- ============================================================================
-- The database is now ready for use with the Sapphire ITSM Platform.
-- 
-- Connection string:
--   postgresql://sapphire:sapphire@localhost:5432/sapphire_support
--
-- Remember to change the password in production!
-- ============================================================================

