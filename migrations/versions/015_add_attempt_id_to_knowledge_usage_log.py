"""Add attempt_id to knowledge_usage_log

Revision ID: 015
Revises: 013
Create Date: 2026-01-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """Add attempt_id column to knowledge_usage_log table to link help requests to specific attempts."""
    
    # Add attempt_id column as nullable foreign key to knowledge_question_attempts
    op.add_column('knowledge_usage_log',
        sa.Column('attempt_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_knowledge_usage_log_attempt_id',
        'knowledge_usage_log',
        'knowledge_question_attempts',
        ['attempt_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for efficient queries
    op.create_index(
        'idx_usage_log_attempt_id',
        'knowledge_usage_log',
        ['attempt_id']
    )


def downgrade():
    """Remove attempt_id column from knowledge_usage_log table."""
    
    op.drop_index('idx_usage_log_attempt_id', table_name='knowledge_usage_log')
    op.drop_constraint('fk_knowledge_usage_log_attempt_id', 'knowledge_usage_log', type_='foreignkey')
    op.drop_column('knowledge_usage_log', 'attempt_id')
