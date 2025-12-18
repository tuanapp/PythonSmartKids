"""Add llm_models table for tracking available AI models across providers

Revision ID: 012
Revises: 011
Create Date: 2025-12-18

This migration creates a table to track LLM models:
- Supports multiple providers (Google, Groq, Anthropic, OpenAI)
- Enables manual override for custom models
- Tracks deprecation status for historical reference
- Maintains display ordering for UI
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create llm_models table."""
    op.create_table(
        'llm_models',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('model_name', sa.String(150), nullable=False, unique=True),  # Provider-native name
        sa.Column('display_name', sa.String(150), nullable=True),  # Human-readable name
        sa.Column('provider', sa.String(50), nullable=False, index=True),  # 'google', 'groq', etc.
        sa.Column('model_type', sa.String(50), nullable=True),  # 'flash', 'pro', etc.
        sa.Column('version', sa.String(20), nullable=True),  # '2.0', '2.5', etc.
        sa.Column('order_number', sa.Integer(), nullable=False, default=0, index=True),  # Display order
        sa.Column('active', sa.Boolean(), nullable=False, default=True),  # Only active returned in API
        sa.Column('deprecated', sa.Boolean(), nullable=False, default=False),  # Old models marked deprecated
        sa.Column('manual', sa.Boolean(), nullable=False, default=False),  # manual=true: never auto-updated
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),  # Last seen in provider API
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create partial indexes for common queries
    op.create_index('idx_llm_models_active', 'llm_models', ['active'], postgresql_where=sa.text('active = TRUE'))
    op.create_index('idx_llm_models_deprecated', 'llm_models', ['deprecated'], postgresql_where=sa.text('deprecated = TRUE'))


def downgrade() -> None:
    """Drop llm_models table."""
    op.drop_index('idx_llm_models_deprecated', table_name='llm_models')
    op.drop_index('idx_llm_models_active', table_name='llm_models')
    op.drop_table('llm_models')
