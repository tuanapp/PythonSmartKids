-- Migration: Add refund tracking to subscription_history
-- Date: 2026-01-15
-- Description: Adds refund_reason column to track refund details and improve audit trail

-- Add refund_reason column to subscription_history
ALTER TABLE subscription_history ADD COLUMN IF NOT EXISTS refund_reason VARCHAR(500) DEFAULT NULL;

-- Add index for efficient refund queries
CREATE INDEX IF NOT EXISTS idx_subscription_history_refund_reason 
ON subscription_history(refund_reason) 
WHERE refund_reason IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN subscription_history.refund_reason IS 'Reason for refund when event is REFUND (manual or webhook-triggered)';
