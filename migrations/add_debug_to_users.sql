-- Add is_debug column to users table
-- When is_debug=TRUE, API debug panel is enabled in frontend
-- When is_debug=FALSE (default), debug panel is hidden

-- Add the column as nullable first
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_debug BOOLEAN;

-- Set default value for existing rows
UPDATE users SET is_debug = FALSE WHERE is_debug IS NULL;

-- Make column non-nullable with default
ALTER TABLE users ALTER COLUMN is_debug SET NOT NULL;
ALTER TABLE users ALTER COLUMN is_debug SET DEFAULT FALSE;
