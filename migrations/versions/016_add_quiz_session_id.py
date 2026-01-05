"""Add quiz_session_id to knowledge_usage_log

Revision ID: 016
Revises: 015
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    """Add quiz_session_id column to knowledge_usage_log and knowledge_question_attempts tables."""
    
    # Add quiz_session_id column to knowledge_usage_log
    op.add_column('knowledge_usage_log',
        sa.Column('quiz_session_id', sa.String(36), nullable=True)
    )
    
    # Add index for efficient queries by session
    op.create_index(
        'idx_usage_log_quiz_session_id',
        'knowledge_usage_log',
        ['quiz_session_id']
    )

    # Add quiz_session_id column to knowledge_question_attempts
    op.add_column('knowledge_question_attempts',
        sa.Column('quiz_session_id', sa.String(36), nullable=True)
    )
    
    # Add index for efficient queries by session
    op.create_index(
        'idx_attempts_quiz_session_id',
        'knowledge_question_attempts',
        ['quiz_session_id']
    )


def downgrade():
    """Remove quiz_session_id column."""
    op.drop_index('idx_usage_log_quiz_session_id', table_name='knowledge_usage_log')
    op.drop_column('knowledge_usage_log', 'quiz_session_id')
    
    op.drop_index('idx_attempts_quiz_session_id', table_name='knowledge_question_attempts')
    op.drop_column('knowledge_question_attempts', 'quiz_session_id')
