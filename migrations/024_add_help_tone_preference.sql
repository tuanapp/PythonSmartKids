-- Migration: 024_add_help_tone_preference.sql
-- Add help_tone_preference column to users table
-- This stores user's preferred difficulty level for AI-generated help explanations
-- Options: NULL (defaults to "kid"), "auto" (grade-1), "kid", or "1"-"12"

ALTER TABLE users ADD COLUMN IF NOT EXISTS help_tone_preference VARCHAR(10) DEFAULT NULL;

COMMENT ON COLUMN users.help_tone_preference IS 'Preferred help explanation tone: NULL/kid=simple, auto=grade-1, or specific grade 1-12';

-- Create index for better query performance on help generation
CREATE INDEX IF NOT EXISTS idx_users_help_tone_preference ON users(help_tone_preference);
