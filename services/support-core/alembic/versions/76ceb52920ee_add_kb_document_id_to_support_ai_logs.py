"""add_kb_document_id_to_support_ai_logs

Revision ID: 76ceb52920ee
Revises: 7c4915b0161c
Create Date: 2025-12-26 11:49:29.531732

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '76ceb52920ee'
down_revision = '7c4915b0161c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('support_ai_logs', sa.Column('kb_document_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('support_ai_logs', 'kb_document_id')

