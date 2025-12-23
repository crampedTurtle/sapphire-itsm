-- ============================================================================
-- Sapphire ITSM Platform - Database and User Creation Script
-- ============================================================================
-- This script creates the database and user. Run this as the postgres superuser
-- before running database_setup.sql
--
-- Usage:
--   psql -U postgres -f database_create_user.sql
-- ============================================================================

-- Create database
CREATE DATABASE sapphire_support;

-- Create user and grant privileges
CREATE USER sapphire WITH PASSWORD 'sapphire';

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE sapphire_support TO sapphire;

-- Note: The main database_setup.sql script will handle schema-level grants
-- after connecting to the database.

