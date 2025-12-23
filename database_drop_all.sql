-- ============================================================================
-- Sapphire ITSM Platform - Drop All Tables and Types Script
-- ============================================================================
-- This script drops all tables, triggers, functions, and enums.
-- WARNING: This will delete all data!
--
-- Usage:
--   psql -U sapphire -d sapphire_support -f database_drop_all.sql
-- ============================================================================

-- ============================================================================
-- 1. DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_onboarding_sessions_last_updated_at ON onboarding_sessions;
DROP TRIGGER IF EXISTS update_tenant_entitlements_updated_at ON tenant_entitlements;
DROP TRIGGER IF EXISTS update_cases_updated_at ON cases;

-- ============================================================================
-- 2. DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS update_updated_at_column();

-- ============================================================================
-- 3. DROP TABLES (in reverse dependency order)
-- ============================================================================

-- Drop tables that reference other tables first
DROP TABLE IF EXISTS tenant_entitlements CASCADE;
DROP TABLE IF EXISTS onboarding_steps CASCADE;
DROP TABLE IF EXISTS onboarding_sessions CASCADE;
DROP TABLE IF EXISTS crm_events CASCADE;
DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS sla_events CASCADE;
DROP TABLE IF EXISTS sla_policies CASCADE;
DROP TABLE IF EXISTS ai_artifacts CASCADE;
DROP TABLE IF EXISTS case_messages CASCADE;
DROP TABLE IF EXISTS cases CASCADE;
DROP TABLE IF EXISTS intent_classifications CASCADE;
DROP TABLE IF EXISTS intake_events CASCADE;
DROP TABLE IF EXISTS identities CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;

-- ============================================================================
-- 4. DROP ENUMS
-- ============================================================================

DROP TYPE IF EXISTS onboardingtrigger CASCADE;
DROP TYPE IF EXISTS onboardingstatus CASCADE;
DROP TYPE IF EXISTS onboardingphase CASCADE;
DROP TYPE IF EXISTS slaeventtype CASCADE;
DROP TYPE IF EXISTS artifacttype CASCADE;
DROP TYPE IF EXISTS sendertype CASCADE;
DROP TYPE IF EXISTS casecategory CASCADE;
DROP TYPE IF EXISTS casepriority CASCADE;
DROP TYPE IF EXISTS casestatus CASCADE;
DROP TYPE IF EXISTS recommendedaction CASCADE;
DROP TYPE IF EXISTS urgency CASCADE;
DROP TYPE IF EXISTS intent CASCADE;
DROP TYPE IF EXISTS intakesource CASCADE;
DROP TYPE IF EXISTS identityrole CASCADE;
DROP TYPE IF EXISTS plantier CASCADE;

-- ============================================================================
-- All tables and types dropped!
-- ============================================================================
-- You can now run database_setup.sql or database_schema_only.sql to recreate
-- everything fresh.
-- ============================================================================

