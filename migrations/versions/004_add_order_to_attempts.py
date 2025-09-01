"""Add qorder column to attempts table

Revision ID: 004
Revises: 003
Create Date: 2025-08-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    """Add qorder column to attempts table to maintain question sequence."""
    # Add the qorder column as nullable integer
    op.add_column('attempts', sa.Column('qorder', sa.Integer(), nullable=True))
    
    # Create an index on the qorder column for better query performance
    op.create_index('ix_attempts_qorder', 'attempts', ['qorder'])

def downgrade():
    """Remove qorder column from attempts table."""
    # Drop the index first
    op.drop_index('ix_attempts_qorder', table_name='attempts')
    
    # Drop the qorder column
    op.drop_column('attempts', 'qorder')
