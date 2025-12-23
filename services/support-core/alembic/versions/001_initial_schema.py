"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def create_enum_if_not_exists(enum_name, enum_values):
    """Create PostgreSQL ENUM type if it doesn't exist"""
    # Escape enum name and values for safety
    enum_name_escaped = enum_name.replace('"', '""')
    values_str = ", ".join([f"'{v.replace(\"'\", \"''\")}'" for v in enum_values])
    # Use DO block to check and create atomically
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name_escaped}') THEN
                CREATE TYPE "{enum_name_escaped}" AS ENUM ({values_str});
            END IF;
        END $$;
    """)


def upgrade() -> None:
    # Create ENUM types if they don't exist (in case database was set up with SQL scripts)
    create_enum_if_not_exists('plantier', ['tier0', 'tier1', 'tier2'])
    create_enum_if_not_exists('identityrole', ['customer', 'agent', 'ops'])
    create_enum_if_not_exists('intakesource', ['email', 'portal'])
    create_enum_if_not_exists('intent', ['sales', 'support', 'onboarding', 'billing', 'compliance', 'outage', 'unknown'])
    create_enum_if_not_exists('urgency', ['low', 'normal', 'high', 'critical'])
    create_enum_if_not_exists('recommendedaction', ['self_service', 'create_case', 'route_sales', 'escalate_ops', 'needs_review'])
    create_enum_if_not_exists('casestatus', ['new', 'open', 'pending_customer', 'pending_internal', 'escalated', 'resolved', 'closed'])
    create_enum_if_not_exists('casepriority', ['low', 'normal', 'high', 'critical'])
    create_enum_if_not_exists('casecategory', ['support', 'onboarding', 'billing', 'compliance', 'outage'])
    create_enum_if_not_exists('sendertype', ['customer', 'agent', 'system'])
    create_enum_if_not_exists('artifacttype', ['summary', 'draft_reply', 'kb_answer'])
    create_enum_if_not_exists('slaeventtype', ['started', 'first_response', 'breached_first_response', 'breached_resolution', 'paused', 'resumed'])
    
    # Tenants
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('primary_domain', sa.String(), nullable=True, unique=True, index=True),
        sa.Column('plan_tier', sa.Enum('tier0', 'tier1', 'tier2', name='plantier'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Identities
    op.create_table(
        'identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(), nullable=False, index=True),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('role', sa.Enum('customer', 'agent', 'ops', name='identityrole'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Intake Events
    op.create_table(
        'intake_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.Enum('email', 'portal', name='intakesource'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('from_email', sa.String(), nullable=False, index=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('body_text', sa.String(), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    
    # Intent Classifications
    op.create_table(
        'intent_classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('intake_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intake_events.id'), nullable=False, index=True),
        sa.Column('intent', sa.Enum('sales', 'support', 'onboarding', 'billing', 'compliance', 'outage', 'unknown', name='intent'), nullable=False),
        sa.Column('urgency', sa.Enum('low', 'normal', 'high', 'critical', name='urgency'), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('compliance_flag', sa.Boolean(), nullable=False),
        sa.Column('recommended_action', sa.Enum('self_service', 'create_case', 'route_sales', 'escalate_ops', 'needs_review', name='recommendedaction'), nullable=False),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Cases
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('external_source', sa.String(), nullable=True),
        sa.Column('external_case_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('new', 'open', 'pending_customer', 'pending_internal', 'escalated', 'resolved', 'closed', name='casestatus'), nullable=False, index=True),
        sa.Column('priority', sa.Enum('low', 'normal', 'high', 'critical', name='casepriority'), nullable=False, index=True),
        sa.Column('category', sa.Enum('support', 'onboarding', 'billing', 'compliance', 'outage', name='casecategory'), nullable=False),
        sa.Column('created_by_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), nullable=True),
        sa.Column('owner_identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Case Messages
    op.create_table(
        'case_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False, index=True),
        sa.Column('sender_type', sa.Enum('customer', 'agent', 'system', name='sendertype'), nullable=False),
        sa.Column('sender_email', sa.String(), nullable=False),
        sa.Column('body_text', sa.String(), nullable=False),
        sa.Column('attachments', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    
    # AI Artifacts
    op.create_table(
        'ai_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=True, index=True),
        sa.Column('intake_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intake_events.id'), nullable=True, index=True),
        sa.Column('artifact_type', sa.Enum('summary', 'draft_reply', 'kb_answer', name='artifacttype'), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('citations', postgresql.JSONB(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('prompt_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # SLA Policies
    op.create_table(
        'sla_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('tier', sa.Enum('tier0', 'tier1', 'tier2', name='plantier'), nullable=False),
        sa.Column('first_response_minutes', sa.Integer(), nullable=False),
        sa.Column('resolution_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # SLA Events
    op.create_table(
        'sla_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=False, index=True),
        sa.Column('event_type', sa.Enum('started', 'first_response', 'breached_first_response', 'breached_resolution', 'paused', 'resumed', name='slaeventtype'), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    
    # Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id'), nullable=True, index=True),
        sa.Column('intake_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('intake_events.id'), nullable=True, index=True),
        sa.Column('event_type', sa.String(), nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )
    
    # CRM Events
    op.create_table(
        'crm_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True, index=True),
        sa.Column('event_type', sa.String(), nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('crm_events')
    op.drop_table('audit_events')
    op.drop_table('sla_events')
    op.drop_table('sla_policies')
    op.drop_table('ai_artifacts')
    op.drop_table('case_messages')
    op.drop_table('cases')
    op.drop_table('intent_classifications')
    op.drop_table('intake_events')
    op.drop_table('identities')
    op.drop_table('tenants')

