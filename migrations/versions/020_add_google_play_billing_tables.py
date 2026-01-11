"""Add Google Play billing tables

Revision ID: 020
Revises: 019
Create Date: 2026-01-09

This migration adds two tables for Google Play billing integration:
1. google_play_purchases - Tracks all Google Play purchases (subscriptions and one-time products)
2. subscription_history - Logs all subscription status changes and credit grants

The google_play_purchases table stores:
- Purchase tokens (unique identifier from Google)
- Product IDs (SKU from Google Play Console)
- Order IDs and purchase state
- Raw receipt data in JSONB format
- Auto-renewing status for subscriptions

The subscription_history table logs:
- Subscription level changes (old -> new)
- Purchase references
- Credits granted (if applicable)
- Event types (STARTED, RENEWED, CANCELLED, EXPIRED, PAUSED)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Google Play billing tables."""
    
    # Create google_play_purchases table
    op.create_table(
        'google_play_purchases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uid', sa.String(), nullable=False, index=True, comment='Firebase User UID'),
        sa.Column('purchase_token', sa.Text(), nullable=False, unique=True, comment='Google Play purchase token (unique identifier)'),
        sa.Column('product_id', sa.String(100), nullable=False, index=True, comment='Product SKU from Google Play Console'),
        sa.Column('order_id', sa.String(100), nullable=True, index=True, comment='Google Play order ID'),
        sa.Column('purchase_time', sa.TIMESTAMP(timezone=True), nullable=False, comment='When purchase was made'),
        sa.Column('purchase_state', sa.Integer(), nullable=False, default=0, comment='0=purchased, 1=cancelled, 2=pending'),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, default=False, comment='Whether purchase was acknowledged'),
        sa.Column('auto_renewing', sa.Boolean(), nullable=True, comment='For subscriptions: whether auto-renew is enabled'),
        sa.Column('raw_receipt', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Full Google Play receipt data'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    
    # Create indexes for google_play_purchases
    op.create_index('ix_google_play_purchases_uid', 'google_play_purchases', ['uid'])
    op.create_index('ix_google_play_purchases_product_id', 'google_play_purchases', ['product_id'])
    op.create_index('ix_google_play_purchases_order_id', 'google_play_purchases', ['order_id'])
    op.create_index('ix_google_play_purchases_purchase_time', 'google_play_purchases', ['purchase_time'])
    
    # Create subscription_history table
    op.create_table(
        'subscription_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uid', sa.String(), nullable=False, index=True, comment='Firebase User UID'),
        sa.Column('purchase_id', sa.Integer(), nullable=True, comment='FK to google_play_purchases.id'),
        sa.Column('event', sa.String(50), nullable=False, comment='STARTED, RENEWED, CANCELLED, EXPIRED, PAUSED, MANUAL'),
        sa.Column('old_subscription', sa.Integer(), nullable=True, comment='Previous subscription level'),
        sa.Column('new_subscription', sa.Integer(), nullable=True, comment='New subscription level'),
        sa.Column('credits_granted', sa.Integer(), nullable=True, default=0, comment='Credits added during this event'),
        sa.Column('performed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True, comment='Additional context or reason'),
    )
    
    # Create indexes for subscription_history
    op.create_index('ix_subscription_history_uid', 'subscription_history', ['uid'])
    op.create_index('ix_subscription_history_event', 'subscription_history', ['event'])
    op.create_index('ix_subscription_history_performed_at', 'subscription_history', ['performed_at'])
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_google_play_purchases_uid',
        'google_play_purchases', 'users',
        ['uid'], ['uid'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_subscription_history_uid',
        'subscription_history', 'users',
        ['uid'], ['uid'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_subscription_history_purchase_id',
        'subscription_history', 'google_play_purchases',
        ['purchase_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop Google Play billing tables."""
    
    # Drop foreign key constraints first
    op.drop_constraint('fk_subscription_history_purchase_id', 'subscription_history', type_='foreignkey')
    op.drop_constraint('fk_subscription_history_uid', 'subscription_history', type_='foreignkey')
    op.drop_constraint('fk_google_play_purchases_uid', 'google_play_purchases', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_subscription_history_performed_at', table_name='subscription_history')
    op.drop_index('ix_subscription_history_event', table_name='subscription_history')
    op.drop_index('ix_subscription_history_uid', table_name='subscription_history')
    
    op.drop_index('ix_google_play_purchases_purchase_time', table_name='google_play_purchases')
    op.drop_index('ix_google_play_purchases_order_id', table_name='google_play_purchases')
    op.drop_index('ix_google_play_purchases_product_id', table_name='google_play_purchases')
    op.drop_index('ix_google_play_purchases_uid', table_name='google_play_purchases')
    
    # Drop tables
    op.drop_table('subscription_history')
    op.drop_table('google_play_purchases')
