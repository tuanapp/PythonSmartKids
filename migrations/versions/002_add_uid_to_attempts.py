"""Add uid field to attempts table

Revision ID: 002
Revises: 001
Create Date: 2025-06-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add uid column to attempts table (nullable initially to allow migration of existing data)
    op.add_column('attempts', sa.Column('uid', sa.String(), nullable=True))
    
    # If you want to set a default value for existing records during migration:
    # For example, set a default value 'legacy_user' for existing records
    op.execute("UPDATE attempts SET uid = 'legacy_user' WHERE uid IS NULL")
    
    # Then make the column non-nullable after populating it
    op.alter_column('attempts', 'uid', nullable=False)


def downgrade() -> None:
    # Remove uid column from attempts table
    op.drop_column('attempts', 'uid')
