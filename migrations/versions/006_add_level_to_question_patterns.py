"""Add level column to question_patterns table

Revision ID: 006
Revises: 005
Create Date: 2025-09-01 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    """Add level column to question_patterns table for difficulty tracking."""
    # Add the level column as nullable integer
    op.add_column('question_patterns', sa.Column('level', sa.Integer(), nullable=True))

def downgrade():
    """Remove level column from question_patterns table."""
    # Drop the level column
    op.drop_column('question_patterns', 'level')
