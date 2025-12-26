"""add_ai_confidence_and_tier_route_to_cases

Revision ID: 4dc73e163b72
Revises: 002_add_onboarding
Create Date: 2025-12-26 11:34:49.297303

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4dc73e163b72'
down_revision = '002_add_onboarding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ai_confidence column (nullable, for existing cases)
    op.add_column('cases', sa.Column('ai_confidence', sa.Float(), nullable=True))
    
    # Add tier_route column (nullable, for existing cases)
    op.add_column('cases', sa.Column('tier_route', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('cases', 'tier_route')
    op.drop_column('cases', 'ai_confidence')

