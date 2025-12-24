"""Add onboarding and tier lifecycle

Revision ID: 002_add_onboarding
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_onboarding'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def create_enum_if_not_exists(enum_name, enum_values):
    """Create PostgreSQL ENUM type if it doesn't exist"""
    # Escape enum name and values for safety
    enum_name_escaped = enum_name.replace('"', '""')
    values_str = ", ".join(["'" + v.replace("'", "''") + "'" for v in enum_values])
    # Use DO block to check and create atomically
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name_escaped}') THEN
                CREATE TYPE "{enum_name_escaped}" AS ENUM ({values_str});
            END IF;
        END $$;
    """)


def upgrade() -> None:
    # Create ENUM types if they don't exist
    create_enum_if_not_exists('onboardingphase', ['not_started', 'phase_0_provisioned', 'phase_1_first_value', 'phase_2_core_workflows', 'phase_3_independent', 'completed', 'paused', 'failed'])
    create_enum_if_not_exists('onboardingstatus', ['active', 'paused', 'completed', 'failed'])
    create_enum_if_not_exists('onboardingtrigger', ['supabase_registration', 'tier_upgrade', 'manual_restart'])
    
    # Onboarding Sessions
    op.create_table(
        'onboarding_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, unique=True, index=True),
        sa.Column('current_phase', sa.Enum('not_started', 'phase_0_provisioned', 'phase_1_first_value', 'phase_2_core_workflows', 'phase_3_independent', 'completed', 'paused', 'failed', name='onboardingphase', create_type=False), nullable=False),
        sa.Column('status', sa.Enum('active', 'paused', 'completed', 'failed', name='onboardingstatus', create_type=False), nullable=False),
        sa.Column('trigger_source', sa.Enum('supabase_registration', 'tier_upgrade', 'manual_restart', name='onboardingtrigger', create_type=False), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False),
    )
    
    # Onboarding Steps
    op.create_table(
        'onboarding_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('onboarding_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('onboarding_sessions.id'), nullable=False, index=True),
        sa.Column('phase', sa.Enum('not_started', 'phase_0_provisioned', 'phase_1_first_value', 'phase_2_core_workflows', 'phase_3_independent', 'completed', 'paused', 'failed', name='onboardingphase', create_type=False), nullable=False),
        sa.Column('step_key', sa.String(), nullable=False),
        sa.Column('step_label', sa.String(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('step_metadata', postgresql.JSONB(), nullable=True),
    )
    
    # Tenant Entitlements
    op.create_table(
        'tenant_entitlements',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), primary_key=True),
        sa.Column('plan_tier', sa.String(), nullable=False),
        sa.Column('sla_policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sla_policies.id'), nullable=True),
        sa.Column('portal_enabled', sa.Boolean(), nullable=False),
        sa.Column('freescout_enabled', sa.Boolean(), nullable=False),
        sa.Column('ai_features', postgresql.JSONB(), nullable=True),
        sa.Column('effective_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('tenant_entitlements')
    op.drop_table('onboarding_steps')
    op.drop_table('onboarding_sessions')

