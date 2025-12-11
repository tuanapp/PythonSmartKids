"""Add credit_usage table to track daily credit usage per user, game, and subject

Revision ID: 011
Revises: 010
Create Date: 2025-12-11

This migration creates a table to track credit usage:
- Tracks usage per user, per day, per game type, per subject
- Allows for future sub-section tracking
- Enables reporting and analytics on credit consumption
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create credit_usage table."""
    op.create_table(
        'credit_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uid', sa.String(), nullable=False, index=True),  # Firebase User UID
        sa.Column('usage_date', sa.Date(), nullable=False, index=True),  # Date of usage (for daily tracking)
        sa.Column('game_type', sa.String(50), nullable=False, index=True),  # 'math', 'dictation', 'knowledge', etc.
        sa.Column('subject', sa.String(100), nullable=True, index=True),  # Subject within game (e.g., 'addition', 'spelling')
        sa.Column('sub_section', sa.String(100), nullable=True),  # Future: sub-section within subject
        sa.Column('credits_used', sa.Integer(), nullable=False, default=1),  # Number of credits used
        sa.Column('generation_count', sa.Integer(), nullable=False, default=1),  # Number of AI generations
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create unique constraint for upsert (one record per user/date/game/subject combination)
    op.create_unique_constraint(
        'uq_credit_usage_uid_date_game_subject',
        'credit_usage',
        ['uid', 'usage_date', 'game_type', 'subject']
    )
    
    # Create composite index for efficient daily lookups
    op.create_index(
        'ix_credit_usage_uid_date_game',
        'credit_usage',
        ['uid', 'usage_date', 'game_type']
    )


def downgrade() -> None:
    """Drop credit_usage table."""
    op.drop_index('ix_credit_usage_uid_date_game', table_name='credit_usage')
    op.drop_constraint('uq_credit_usage_uid_date_game_subject', 'credit_usage', type_='unique')
    op.drop_table('credit_usage')
