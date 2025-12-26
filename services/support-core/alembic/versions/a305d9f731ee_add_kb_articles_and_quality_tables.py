"""add_kb_articles_and_quality_tables

Revision ID: a305d9f731ee
Revises: 76ceb52920ee
Create Date: 2025-12-26 11:56:48.352429

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a305d9f731ee'
down_revision = '76ceb52920ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create kb_articles_index table
    op.create_table(
        'kb_articles_index',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('outline_document_id', sa.String(), nullable=False, unique=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tenant_level', sa.String(), nullable=False, server_default='global'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('embedding', postgresql.JSONB(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    )
    op.create_index(op.f('ix_kb_articles_index_outline_document_id'), 'kb_articles_index', ['outline_document_id'], unique=True)
    op.create_index(op.f('ix_kb_articles_index_tenant_id'), 'kb_articles_index', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_kb_articles_index_last_updated_at'), 'kb_articles_index', ['last_updated_at'], unique=False)
    
    # Create kb_article_revisions table
    op.create_table(
        'kb_article_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('outline_document_id', sa.String(), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(), nullable=False, server_default='ai'),
        sa.ForeignKeyConstraint(['article_id'], ['kb_articles_index.id'], ),
    )
    op.create_index(op.f('ix_kb_article_revisions_outline_document_id'), 'kb_article_revisions', ['outline_document_id'], unique=False)
    op.create_index(op.f('ix_kb_article_revisions_created_at'), 'kb_article_revisions', ['created_at'], unique=False)
    
    # Create kb_decision_logs table
    op.create_table(
        'kb_decision_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('support_log_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('similarity_score', sa.String(), nullable=True),
        sa.Column('outline_document_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['support_log_id'], ['support_ai_logs.id'], ),
    )
    op.create_index(op.f('ix_kb_decision_logs_support_log_id'), 'kb_decision_logs', ['support_log_id'], unique=False)
    op.create_index(op.f('ix_kb_decision_logs_timestamp'), 'kb_decision_logs', ['timestamp'], unique=False)
    
    # Create kb_quality_scores table
    op.create_table(
        'kb_quality_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('outline_document_id', sa.String(), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version_revision_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('clarity_score', sa.Integer(), nullable=False),
        sa.Column('completeness_score', sa.Integer(), nullable=False),
        sa.Column('technical_accuracy_score', sa.Integer(), nullable=False),
        sa.Column('structure_score', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['article_id'], ['kb_articles_index.id'], ),
        sa.ForeignKeyConstraint(['version_revision_id'], ['kb_article_revisions.id'], ),
    )
    op.create_index(op.f('ix_kb_quality_scores_outline_document_id'), 'kb_quality_scores', ['outline_document_id'], unique=False)
    op.create_index(op.f('ix_kb_quality_scores_created_at'), 'kb_quality_scores', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_kb_quality_scores_created_at'), table_name='kb_quality_scores')
    op.drop_index(op.f('ix_kb_quality_scores_outline_document_id'), table_name='kb_quality_scores')
    op.drop_table('kb_quality_scores')
    op.drop_index(op.f('ix_kb_decision_logs_timestamp'), table_name='kb_decision_logs')
    op.drop_index(op.f('ix_kb_decision_logs_support_log_id'), table_name='kb_decision_logs')
    op.drop_table('kb_decision_logs')
    op.drop_index(op.f('ix_kb_article_revisions_created_at'), table_name='kb_article_revisions')
    op.drop_index(op.f('ix_kb_article_revisions_outline_document_id'), table_name='kb_article_revisions')
    op.drop_table('kb_article_revisions')
    op.drop_index(op.f('ix_kb_articles_index_last_updated_at'), table_name='kb_articles_index')
    op.drop_index(op.f('ix_kb_articles_index_tenant_id'), table_name='kb_articles_index')
    op.drop_index(op.f('ix_kb_articles_index_outline_document_id'), table_name='kb_articles_index')
    op.drop_table('kb_articles_index')

