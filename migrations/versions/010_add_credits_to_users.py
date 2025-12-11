"""Add credits column to users table for AI generation limits

Revision ID: 010
Revises: 009
Create Date: 2025-12-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """Add credits column to users table.
    
    New users get 10 credits by default.
    Each AI generation request costs 1 credit.
    Premium users (subscription >= 2) will have high credits set manually.
    When credits reach 0, user cannot generate AI requests.
    """
    op.add_column(
        'users',
        sa.Column('credits', sa.Integer(), nullable=False, server_default='10')
    )
    
    # Create index for efficient credit queries
    op.create_index('idx_users_credits', 'users', ['credits'])


def downgrade():
    """Remove credits column from users table."""
    op.drop_index('idx_users_credits', table_name='users')
    op.drop_column('users', 'credits')
