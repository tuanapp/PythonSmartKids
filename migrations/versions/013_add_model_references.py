"""Add model_id FK references to tracking tables

Revision ID: 013
Revises: 012
Create Date: 2025-12-18

This migration adds model_id foreign key to:
- credit_usage (primary AI usage tracking)
- attempts (math question attempts)
- knowledge_question_attempts (knowledge game attempts)

Existing rows will have NULL for model_id. Only new records will have the FK populated.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add model_id column to tracking tables."""
    
    # Add model_id to credit_usage
    op.add_column(
        'credit_usage',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('idx_credit_usage_model_id', 'credit_usage', ['model_id'])
    
    # Add model_id to attempts
    op.add_column(
        'attempts',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('idx_attempts_model_id', 'attempts', ['model_id'])
    
    # Add model_id to knowledge_question_attempts
    op.add_column(
        'knowledge_question_attempts',
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('idx_knowledge_attempts_model_id', 'knowledge_question_attempts', ['model_id'])


def downgrade() -> None:
    """Remove model_id column from tracking tables."""
    
    # Remove from knowledge_question_attempts
    op.drop_index('idx_knowledge_attempts_model_id', table_name='knowledge_question_attempts')
    op.drop_column('knowledge_question_attempts', 'model_id')
    
    # Remove from attempts
    op.drop_index('idx_attempts_model_id', table_name='attempts')
    op.drop_column('attempts', 'model_id')
    
    # Remove from credit_usage
    op.drop_index('idx_credit_usage_model_id', table_name='credit_usage')
    op.drop_column('credit_usage', 'model_id')
