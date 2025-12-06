# Database Guide

*Last Updated: December 2025*

This guide covers database setup, schema, and migrations for the SmartBoy backend.

## Overview

SmartBoy uses **PostgreSQL** for all environments:
- **Production**: Neon PostgreSQL (cloud)
- **Development**: Local PostgreSQL or Neon

## Quick Reference

### Apply Migrations (Production)
```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

### Check Migration Status
```bash
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=YOUR_KEY"
```

---

## Database Schema

### Current Tables (Migration 008)

#### `users` - User accounts
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uid VARCHAR UNIQUE NOT NULL,          -- Firebase UID
    email VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    grade_level INTEGER NOT NULL,
    subscription INTEGER DEFAULT 0,        -- 0=free, 1=trial, 2+=premium
    registration_date TIMESTAMPTZ NOT NULL,
    
    -- Blocking fields
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,
    blocked_at TIMESTAMPTZ,
    blocked_by VARCHAR,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `prompts` - AI interaction tracking
```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    uid VARCHAR NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
    
    -- Request details
    request_type VARCHAR(50) DEFAULT 'question_generation',
    request_text TEXT NOT NULL,
    model_name VARCHAR(100),
    
    -- Question generation fields
    level INTEGER,                         -- Difficulty level (1-6)
    source VARCHAR(50),                    -- 'api', 'cached', 'fallback'
    
    -- Response details
    response_text TEXT,
    response_time_ms INTEGER,
    
    -- Token tracking
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost_usd FLOAT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    
    -- Metadata
    is_live INTEGER DEFAULT 1,             -- 1=app, 0=test
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_prompts_uid ON prompts(uid);
CREATE INDEX ix_prompts_created_at ON prompts(created_at);
```

#### `attempts` - Student answer tracking
```sql
CREATE TABLE attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    uid VARCHAR NOT NULL,                  -- Firebase UID
    datetime TIMESTAMPTZ NOT NULL,
    question TEXT NOT NULL,
    is_answer_correct BOOLEAN NOT NULL,
    incorrect_answer TEXT,
    correct_answer TEXT NOT NULL,
    qorder INTEGER                         -- Question order in session
);
```

#### `question_patterns` - AI question templates
```sql
CREATE TABLE question_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR NOT NULL,                 -- e.g., 'algebra', 'fraction'
    pattern_text TEXT NOT NULL,
    notes TEXT,                            -- Special formatting notes
    level INTEGER,                         -- Difficulty level
    created_at TIMESTAMPTZ NOT NULL
);
```

#### `user_blocking_history` - Blocking audit trail
```sql
CREATE TABLE user_blocking_history (
    id SERIAL PRIMARY KEY,
    user_uid VARCHAR NOT NULL,
    action VARCHAR NOT NULL,               -- 'BLOCKED' or 'UNBLOCKED'
    reason TEXT,
    blocked_at TIMESTAMPTZ,
    blocked_by VARCHAR,
    unblocked_at TIMESTAMPTZ,
    notes TEXT
);
```

---

## Configuration

### Environment Variables

```bash
# Database provider (always 'neon')
DATABASE_PROVIDER=neon

# Neon PostgreSQL connection details
NEON_DBNAME=smartboydb
NEON_USER=tuanapp
NEON_PASSWORD=your-password
NEON_HOST=ep-sparkling-butterfly-xxxxx.aws.neon.tech
NEON_SSLMODE=require

# Full connection URL (alternative)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

### Development Environment (`.env.development`)
```bash
DATABASE_PROVIDER=neon
NEON_DBNAME=smartboy_dev
NEON_USER=smartboy_dev
NEON_PASSWORD=smartboy_dev
NEON_HOST=localhost
NEON_SSLMODE=disable
```

### Production Environment (`.env.production`)
```bash
DATABASE_PROVIDER=neon
NEON_DBNAME=smartboydb
NEON_USER=tuanapp
NEON_PASSWORD=your-production-password
NEON_HOST=ep-sparkling-butterfly-xxxxx.aws.neon.tech
NEON_SSLMODE=require
```

---

## Migrations

### How Migrations Work

SmartBoy uses a custom migration system designed for Vercel's serverless environment (Alembic file-based migrations don't work on Vercel).

**Key Features:**
- ✅ **Idempotent** - Safe to run multiple times
- ✅ **Single endpoint** - One command applies all migrations
- ✅ **Automatic table creation** - Creates missing tables
- ✅ **Column updates** - Adds missing columns to existing tables

### Apply All Migrations

```bash
# Production
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"

# Local
curl -X POST "http://localhost:8000/admin/apply-migrations?admin_key=dev-admin-key"
```

### Check Migration Status

```bash
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=YOUR_KEY"
```

**Example Response:**
```json
{
  "current_version": "008",
  "alembic_table_exists": true,
  "existing_tables": ["attempts", "question_patterns", "users", "prompts"],
  "notes_column_exists": true,
  "level_column_exists": true,
  "prompts_table_exists": true,
  "prompts_indexes_exist": true,
  "user_blocking_exists": true,
  "user_blocking_history_exists": true,
  "needs_migration": false
}
```

### Migration History

| Version | Changes |
|---------|---------|
| 001-003 | Base tables (attempts, question_patterns, users) |
| 004 | Notes column on question_patterns |
| 005 | Level column on question_patterns |
| 006 | Subscription column on users |
| 007 | Prompts table with LLM tracking fields |
| 008 | User blocking fields + simplified architecture |

---

## Local PostgreSQL Setup

### Automatic (Recommended)

The application auto-creates the database on localhost when it doesn't exist.

```powershell
.\start-dev.ps1
```

### Manual Setup

#### Option 1: Using psql
```sql
-- Connect as postgres superuser
psql -U postgres

-- Create database and user
CREATE DATABASE smartboy_dev;
CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';
GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;

-- Grant schema permissions
\c smartboy_dev
GRANT ALL ON SCHEMA public TO smartboy_dev;
\q
```

#### Option 2: Using Setup Script
```powershell
.\setup-postgres.ps1
```

#### Option 3: Using pgAdmin
1. Open pgAdmin
2. Create database: `smartboy_dev`
3. Create user: `smartboy_dev` / password: `smartboy_dev`
4. Grant privileges to user on database

### Verify Connection
```bash
psql -h localhost -U smartboy_dev -d smartboy_dev -c "SELECT current_database(), current_user;"
```

---

## Architecture

### Database Layer Organization

```
app/db/
├── __init__.py           # Package initialization
├── db_factory.py         # Factory pattern for providers
├── db_init.py            # Database initialization
├── db_interface.py       # Abstract database interface
├── db_initializer.py     # Schema initialization
├── models.py             # SQLAlchemy models
├── neon_provider.py      # Neon PostgreSQL implementation
└── vercel_migrations.py  # Migration manager for Vercel
```

### Provider Pattern

The application uses a provider pattern for database abstraction:

```python
from app.db.db_factory import DatabaseFactory

# Get the configured provider
db = DatabaseFactory.get_provider()

# Use provider methods
db.init_db()
db.save_attempt(attempt_data)
db.get_attempts_by_uid(uid)
```

### Repository Layer

The `db_service.py` acts as a repository layer:

```python
from app.repositories import db_service

# Save data
db_service.save_attempt(attempt)
db_service.save_user_registration(user)

# Query data
user = db_service.get_user_by_uid(uid)
attempts = db_service.get_attempts_by_uid(uid)
```

---

## Troubleshooting

### Connection Issues

**Problem**: `FATAL: database "smartboy_dev" does not exist`

**Solution**: The app should auto-create this. If it fails:
```powershell
.\setup-postgres.ps1
```

**Problem**: `password authentication failed`

**Solution**: Check pg_hba.conf and ensure:
```
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
```

**Problem**: `psql: command not found`

**Solution**: Add PostgreSQL to PATH:
1. Find install directory (usually `C:\Program Files\PostgreSQL\16\bin`)
2. Add to System PATH
3. Restart PowerShell

### Migration Issues

**Problem**: `Invalid admin key`

**Solution**: Set `ADMIN_KEY` in environment variables

**Problem**: Timeout during migration

**Solution**: Run again - migrations are idempotent and will continue where they left off

**Problem**: `Table already exists`

**Solution**: Normal behavior - migrations skip existing objects

### Direct Database Access

For debugging, connect directly:

```bash
psql "postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Useful queries:
```sql
-- View all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check migration version
SELECT version_num FROM alembic_version;

-- View recent prompts
SELECT * FROM prompts ORDER BY created_at DESC LIMIT 10;

-- Check user subscription
SELECT uid, email, subscription, is_blocked FROM users;
```

---

## Best Practices

1. **Always use migrations** - Don't modify schema directly in production
2. **Test locally first** - Run migrations on development before production
3. **Back up before major changes** - Neon provides point-in-time recovery
4. **Use indexes** - The schema includes indexes for common queries
5. **Monitor connections** - Neon has connection limits based on plan

---

*For deployment-specific database information, see [DEPLOYMENT.md](DEPLOYMENT.md)*
