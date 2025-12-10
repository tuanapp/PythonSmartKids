"""Add game_scores table for leaderboard functionality

Revision ID: 009
Revises: 008
Create Date: 2025-12-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """Create game_scores table for storing game scores for leaderboard.
    
    Stores scores for:
    - multiplication_time: highest correct answers in 100s is the best score
    - multiplication_range: lowest time to complete 88 questions is the best score
    """
    op.create_table(
        'game_scores',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uid', sa.String(100), nullable=False, index=True),
        sa.Column('user_name', sa.String(255), nullable=False),  # Display name for leaderboard
        sa.Column('game_type', sa.String(50), nullable=False, index=True),  # 'multiplication_time' or 'multiplication_range'
        sa.Column('score', sa.Integer(), nullable=False),  # Correct answers for time game
        sa.Column('time_seconds', sa.Integer(), nullable=True),  # Completion time for range game
        sa.Column('total_questions', sa.Integer(), nullable=True),  # Total questions answered
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("game_type IN ('multiplication_time', 'multiplication_range')", name='valid_game_type'),
    )
    
    # Create composite index for efficient leaderboard queries
    op.create_index('idx_game_scores_type_score', 'game_scores', ['game_type', 'score'])
    op.create_index('idx_game_scores_type_time', 'game_scores', ['game_type', 'time_seconds'])


def downgrade():
    """Remove game_scores table."""
    op.drop_index('idx_game_scores_type_time', table_name='game_scores')
    op.drop_index('idx_game_scores_type_score', table_name='game_scores')
    op.drop_table('game_scores')
