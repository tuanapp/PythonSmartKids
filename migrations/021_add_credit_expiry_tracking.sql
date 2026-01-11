-- Migration: Add credit expiry tracking for premium subscriptions
-- Date: 2026-01-11
-- Description: Adds credit expiry fields to track when subscription credits expire

-- Add credits_expire_at column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_expire_at TIMESTAMP DEFAULT NULL;

-- Add index for efficient expiry queries
CREATE INDEX IF NOT EXISTS idx_users_credits_expire_at ON users(credits_expire_at) WHERE credits_expire_at IS NOT NULL;

-- Add expiry_date column to subscription_history for audit trail
ALTER TABLE subscription_history ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN users.credits_expire_at IS 'Timestamp when subscription credits expire (monthly: 30 days, yearly: 365 days)';
COMMENT ON COLUMN subscription_history.expiry_date IS 'Expiry date for credits granted in this subscription event';
