"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-05-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('uid', sa.String(), nullable=False),
        sa.Column('datetime', sa.DateTime(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('is_answer_correct', sa.Boolean(), nullable=False),
        sa.Column('incorrect_answer', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('question_patterns',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('pattern_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('question_patterns')
    op.drop_table('attempts')