"""Add notes column to question_patterns table

Revision ID: 005
Revises: 004
Create Date: 2025-09-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    """Add notes column to question_patterns table for special formatting requirements."""
    # Add the notes column as nullable text
    op.add_column('question_patterns', sa.Column('notes', sa.Text(), nullable=True))

def downgrade():
    """Remove notes column from question_patterns table."""
    # Drop the notes column
    op.drop_column('question_patterns', 'notes')
