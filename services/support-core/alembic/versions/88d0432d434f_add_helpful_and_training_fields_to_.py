"""add_helpful_and_training_fields_to_support_ai_logs

Revision ID: 88d0432d434f
Revises: a305d9f731ee
Create Date: 2025-12-26 11:56:49.782390

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88d0432d434f'
down_revision = 'a305d9f731ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('support_ai_logs', sa.Column('helpful', sa.Boolean(), nullable=True))
    op.add_column('support_ai_logs', sa.Column('used_in_training', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('support_ai_logs', 'used_in_training')
    op.drop_column('support_ai_logs', 'helpful')

