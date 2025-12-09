-- Add debug column to users table
-- When debug=TRUE, API debug panel is enabled in frontend
-- When debug=FALSE (default), debug panel is hidden

-- Add the column as nullable first
ALTER TABLE users ADD COLUMN IF NOT EXISTS debug BOOLEAN;

-- Set default value for existing rows
UPDATE users SET debug = FALSE WHERE debug IS NULL;

-- Make column non-nullable with default
ALTER TABLE users ALTER COLUMN debug SET NOT NULL;
ALTER TABLE users ALTER COLUMN debug SET DEFAULT FALSE;
