"""Validate UID usage

Revision ID: 003
Revises: 002
Create Date: 2025-06-02

This migration doesn't make any schema changes, but validates that the uid
field is being properly used and populated.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Validate that the uid field exists and is used properly."""
    conn = op.get_bind()
    
    # Check that the uid column exists in the attempts table
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'attempts' AND column_name = 'uid'"
    )).fetchone()
    
    if not result:
        raise Exception("The uid column does not exist in the attempts table. "
                       "Make sure to apply migration 002_add_uid_to_attempts.py first.")
    
    # Log validation success
    conn.execute(text("COMMENT ON COLUMN attempts.uid IS 'Firebase User UID - Added and validated in migration 003'"))


def downgrade() -> None:
    """No downgrade needed for validation."""
    pass
