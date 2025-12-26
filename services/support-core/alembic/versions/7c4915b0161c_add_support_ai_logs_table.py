"""add_support_ai_logs_table

Revision ID: 7c4915b0161c
Revises: 4dc73e163b72
Create Date: 2025-12-26 11:40:58.565278

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7c4915b0161c'
down_revision = '4dc73e163b72'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'support_ai_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('ai_answer', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('follow_up_flag', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escalation_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('citations', postgresql.JSONB(), nullable=True),
        sa.Column('context_docs', postgresql.JSONB(), nullable=True),
        sa.Column('user_feedback', sa.String(), nullable=True),
        sa.Column('model_used', sa.String(), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    )
    op.create_index(op.f('ix_support_ai_logs_tenant_id'), 'support_ai_logs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_support_ai_logs_case_id'), 'support_ai_logs', ['case_id'], unique=False)
    op.create_index(op.f('ix_support_ai_logs_created_at'), 'support_ai_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_support_ai_logs_created_at'), table_name='support_ai_logs')
    op.drop_index(op.f('ix_support_ai_logs_case_id'), table_name='support_ai_logs')
    op.drop_index(op.f('ix_support_ai_logs_tenant_id'), table_name='support_ai_logs')
    op.drop_table('support_ai_logs')

