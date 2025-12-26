-- ============================================================================
-- Sapphire ITSM Platform - KB & AI Improvement System Tables
-- ============================================================================
-- This script creates all tables and columns for the closed-loop KB + AI
-- improvement system, including:
--   - KB articles index and revisions
--   - KB decision logs
--   - KB quality scores
--   - Updates to cases and support_ai_logs tables
--
-- Usage:
--   psql -U sapphire -d sapphire_support -f database_kb_improvements.sql
--
-- Note: Run this after the base schema is created (database_setup.sql)
-- ============================================================================

-- ============================================================================
-- 1. CREATE SUPPORT_AI_LOGS TABLE (if it doesn't exist)
-- ============================================================================

CREATE TABLE IF NOT EXISTS support_ai_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    case_id UUID,
    message VARCHAR NOT NULL,
    subject VARCHAR,
    ai_answer VARCHAR NOT NULL,
    confidence FLOAT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    follow_up_flag BOOLEAN NOT NULL DEFAULT FALSE,
    escalation_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    citations JSONB,
    context_docs JSONB,
    user_feedback VARCHAR,
    model_used VARCHAR NOT NULL,
    tier INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add foreign key constraints separately (in case referenced tables don't exist yet)
DO $$
BEGIN
    -- Add tenant foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_support_ai_logs_tenant'
        ) THEN
            ALTER TABLE support_ai_logs 
            ADD CONSTRAINT fk_support_ai_logs_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id);
        END IF;
    END IF;
    
    -- Add case foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cases') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_support_ai_logs_case'
        ) THEN
            ALTER TABLE support_ai_logs 
            ADD CONSTRAINT fk_support_ai_logs_case 
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- Indexes for support_ai_logs
CREATE INDEX IF NOT EXISTS ix_support_ai_logs_tenant_id ON support_ai_logs(tenant_id);
CREATE INDEX IF NOT EXISTS ix_support_ai_logs_case_id ON support_ai_logs(case_id);
CREATE INDEX IF NOT EXISTS ix_support_ai_logs_created_at ON support_ai_logs(created_at);

-- ============================================================================
-- 2. ADD COLUMNS TO EXISTING TABLES
-- ============================================================================

-- Add AI confidence and tier route to cases table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'ai_confidence'
    ) THEN
        ALTER TABLE cases ADD COLUMN ai_confidence FLOAT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'cases' AND column_name = 'tier_route'
    ) THEN
        ALTER TABLE cases ADD COLUMN tier_route INTEGER;
    END IF;
END $$;

-- Add KB and training fields to support_ai_logs table (now that it exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'support_ai_logs' AND column_name = 'kb_document_id'
    ) THEN
        ALTER TABLE support_ai_logs ADD COLUMN kb_document_id VARCHAR;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'support_ai_logs' AND column_name = 'helpful'
    ) THEN
        ALTER TABLE support_ai_logs ADD COLUMN helpful BOOLEAN;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'support_ai_logs' AND column_name = 'used_in_training'
    ) THEN
        ALTER TABLE support_ai_logs ADD COLUMN used_in_training BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- ============================================================================
-- 3. CREATE KB ARTICLES INDEX TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS kb_articles_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outline_document_id VARCHAR NOT NULL UNIQUE,
    title TEXT NOT NULL,
    tags TEXT[],
    tenant_level VARCHAR NOT NULL DEFAULT 'global',
    tenant_id UUID,
    embedding JSONB,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Add foreign key constraint separately
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_kb_articles_tenant'
        ) THEN
            ALTER TABLE kb_articles_index 
            ADD CONSTRAINT fk_kb_articles_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id);
        END IF;
    END IF;
END $$;

-- Indexes for kb_articles_index
CREATE INDEX IF NOT EXISTS ix_kb_articles_index_outline_document_id ON kb_articles_index(outline_document_id);
CREATE INDEX IF NOT EXISTS ix_kb_articles_index_tenant_id ON kb_articles_index(tenant_id);
CREATE INDEX IF NOT EXISTS ix_kb_articles_index_last_updated_at ON kb_articles_index(last_updated_at);

-- ============================================================================
-- 4. CREATE KB ARTICLE REVISIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS kb_article_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outline_document_id VARCHAR NOT NULL,
    article_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR NOT NULL DEFAULT 'ai'
);

-- Add foreign key constraint separately
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'kb_articles_index') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_kb_revisions_article'
        ) THEN
            ALTER TABLE kb_article_revisions 
            ADD CONSTRAINT fk_kb_revisions_article 
            FOREIGN KEY (article_id) REFERENCES kb_articles_index(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

-- Indexes for kb_article_revisions
CREATE INDEX IF NOT EXISTS ix_kb_article_revisions_outline_document_id ON kb_article_revisions(outline_document_id);
CREATE INDEX IF NOT EXISTS ix_kb_article_revisions_created_at ON kb_article_revisions(created_at);

-- ============================================================================
-- 5. CREATE KB DECISION LOGS TABLE
-- ============================================================================
-- Note: This table references support_ai_logs, which is created in section 1

CREATE TABLE IF NOT EXISTS kb_decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    support_log_id UUID,
    decision VARCHAR NOT NULL,
    reason TEXT,
    similarity_score VARCHAR,  -- JSON string with similarity details
    outline_document_id VARCHAR,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add foreign key constraint separately (support_ai_logs should exist by now)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'support_ai_logs') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_kb_decision_logs_support_log'
        ) THEN
            ALTER TABLE kb_decision_logs 
            ADD CONSTRAINT fk_kb_decision_logs_support_log 
            FOREIGN KEY (support_log_id) REFERENCES support_ai_logs(id) ON DELETE SET NULL;
        END IF;
    ELSE
        RAISE NOTICE 'Warning: support_ai_logs table does not exist. Foreign key constraint not added.';
    END IF;
END $$;

-- Indexes for kb_decision_logs
CREATE INDEX IF NOT EXISTS ix_kb_decision_logs_support_log_id ON kb_decision_logs(support_log_id);
CREATE INDEX IF NOT EXISTS ix_kb_decision_logs_timestamp ON kb_decision_logs(timestamp);

-- ============================================================================
-- 6. CREATE KB QUALITY SCORES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS kb_quality_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outline_document_id VARCHAR NOT NULL,
    article_id UUID,
    version_revision_id UUID,
    clarity_score INTEGER NOT NULL,
    completeness_score INTEGER NOT NULL,
    technical_accuracy_score INTEGER NOT NULL,
    structure_score INTEGER NOT NULL,
    overall_score INTEGER NOT NULL,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add foreign key constraints separately
DO $$
BEGIN
    -- Article foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'kb_articles_index') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_kb_quality_scores_article'
        ) THEN
            ALTER TABLE kb_quality_scores 
            ADD CONSTRAINT fk_kb_quality_scores_article 
            FOREIGN KEY (article_id) REFERENCES kb_articles_index(id) ON DELETE SET NULL;
        END IF;
    END IF;
    
    -- Revision foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'kb_article_revisions') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_kb_quality_scores_revision'
        ) THEN
            ALTER TABLE kb_quality_scores 
            ADD CONSTRAINT fk_kb_quality_scores_revision 
            FOREIGN KEY (version_revision_id) REFERENCES kb_article_revisions(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

-- Indexes for kb_quality_scores
CREATE INDEX IF NOT EXISTS ix_kb_quality_scores_outline_document_id ON kb_quality_scores(outline_document_id);
CREATE INDEX IF NOT EXISTS ix_kb_quality_scores_created_at ON kb_quality_scores(created_at);

-- ============================================================================
-- 7. GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON TABLE support_ai_logs TO sapphire;
GRANT ALL PRIVILEGES ON TABLE kb_articles_index TO sapphire;
GRANT ALL PRIVILEGES ON TABLE kb_article_revisions TO sapphire;
GRANT ALL PRIVILEGES ON TABLE kb_decision_logs TO sapphire;
GRANT ALL PRIVILEGES ON TABLE kb_quality_scores TO sapphire;

-- ============================================================================
-- 8. VERIFY CREATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'KB Improvement System tables created successfully!';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - support_ai_logs';
    RAISE NOTICE '  - kb_articles_index';
    RAISE NOTICE '  - kb_article_revisions';
    RAISE NOTICE '  - kb_decision_logs';
    RAISE NOTICE '  - kb_quality_scores';
    RAISE NOTICE 'Columns added to:';
    RAISE NOTICE '  - cases (ai_confidence, tier_route)';
    RAISE NOTICE '  - support_ai_logs (kb_document_id, helpful, used_in_training)';
END $$;

