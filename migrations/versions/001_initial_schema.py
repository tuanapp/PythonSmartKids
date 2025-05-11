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
        sa.Column('datetime', sa.DateTime(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('is_answer_correct', sa.Boolean(), nullable=False),
        sa.Column('incorrect_answer', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('attempts')