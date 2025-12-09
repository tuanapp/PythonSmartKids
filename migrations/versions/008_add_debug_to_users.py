"""Add debug column to users table for API debug panel control

Revision ID: 008
Revises: 007
Create Date: 2025-12-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """Add debug column to users table.
    
    When debug=True, the API debug panel is enabled in the frontend.
    When debug=False (default), the debug panel is hidden.
    """
    # Add debug column with default False
    op.add_column(
        'users',
        sa.Column('debug', sa.Boolean(), nullable=True, default=False)
    )
    
    # Set default value for existing rows
    op.execute("UPDATE users SET debug = FALSE WHERE debug IS NULL")
    
    # Make column non-nullable after setting defaults
    op.alter_column(
        'users',
        'debug',
        nullable=False,
        server_default=sa.text('FALSE')
    )


def downgrade():
    """Remove debug column from users table."""
    op.drop_column('users', 'debug')
