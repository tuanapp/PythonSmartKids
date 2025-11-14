-- Migration: Add user blocking functionality
-- Date: 2025-11-14
-- Description: Create users table with blocking fields and create blocking history table

-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    grade_level INTEGER NOT NULL,
    subscription INTEGER DEFAULT 0 NOT NULL,
    registration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Blocking fields
    is_blocked BOOLEAN DEFAULT FALSE NOT NULL,
    blocked_reason TEXT,
    blocked_at TIMESTAMP WITH TIME ZONE,
    blocked_by VARCHAR(255)
);

-- Create index on uid for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_uid ON users(uid);

-- Create index for faster blocked user queries
CREATE INDEX IF NOT EXISTS idx_users_is_blocked ON users(is_blocked) WHERE is_blocked = TRUE;

-- If users table already exists, add blocking fields (this will fail silently if they exist)
DO $$ 
BEGIN
    BEGIN
        ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE NOT NULL;
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE users ADD COLUMN blocked_reason TEXT;
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE users ADD COLUMN blocked_at TIMESTAMP WITH TIME ZONE;
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE users ADD COLUMN blocked_by VARCHAR(255);
    EXCEPTION
        WHEN duplicate_column THEN NULL;
    END;
END $$;

-- Create user_blocking_history table
CREATE TABLE IF NOT EXISTS user_blocking_history (
    id SERIAL PRIMARY KEY,
    user_uid VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'BLOCKED', 'UNBLOCKED'
    reason TEXT,
    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blocked_by VARCHAR(255),
    unblocked_at TIMESTAMP,
    notes TEXT,
    CONSTRAINT fk_user_blocking_uid FOREIGN KEY (user_uid) REFERENCES users(uid) ON DELETE CASCADE
);

-- Create indexes for blocking history queries
CREATE INDEX IF NOT EXISTS idx_blocking_history_uid ON user_blocking_history(user_uid);
CREATE INDEX IF NOT EXISTS idx_blocking_history_action ON user_blocking_history(action);
CREATE INDEX IF NOT EXISTS idx_blocking_history_blocked_at ON user_blocking_history(blocked_at DESC);

-- Add comments for documentation
COMMENT ON TABLE user_blocking_history IS 'Tracks all user blocking and unblocking actions';
COMMENT ON COLUMN user_blocking_history.action IS 'Action type: BLOCKED or UNBLOCKED';
COMMENT ON COLUMN user_blocking_history.reason IS 'Reason for blocking/unblocking';
COMMENT ON COLUMN user_blocking_history.blocked_by IS 'Admin or system identifier who performed the action';
