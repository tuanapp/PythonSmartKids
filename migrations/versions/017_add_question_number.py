"""Add question_number to knowledge_usage_log

Revision ID: 017
Revises: 016
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    """Add question_number column to knowledge_usage_log table for tracking which question help requests belong to."""
    
    # Add question_number column (nullable since existing records won't have it)
    op.add_column('knowledge_usage_log',
        sa.Column('question_number', sa.Integer, nullable=True)
    )
    
    # Add composite index for efficient queries by session + question
    op.create_index(
        'idx_usage_log_session_question',
        'knowledge_usage_log',
        ['quiz_session_id', 'question_number']
    )


def downgrade():
    """Remove question_number column and index."""
    op.drop_index('idx_usage_log_session_question', table_name='knowledge_usage_log')
    op.drop_column('knowledge_usage_log', 'question_number')
