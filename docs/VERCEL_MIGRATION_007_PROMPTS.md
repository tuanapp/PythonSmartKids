# Vercel Migration Guide - Prompts Table (Migration 007)

## Overview
This guide explains how to migrate the new `prompts` table to your Vercel production database.

## What's Being Added

### New Table: `prompts`
Stores AI prompt requests and responses from the `/generate-questions` endpoint.

**Schema:**
```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    uid TEXT NOT NULL,
    request_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    is_live INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompts_uid ON prompts(uid);
CREATE INDEX idx_prompts_created_at ON prompts(created_at);
```

## Migration Steps

### Option 1: Use Existing Admin API Endpoint (Recommended)

#### Step 1: Check Current Migration Status
```bash
curl -X GET "https://your-vercel-app.vercel.app/admin/migration-status?admin_key=YOUR_ADMIN_KEY"
```

**Expected Response:**
```json
{
  "current_version": "006",
  "alembic_table_exists": true,
  "existing_tables": ["attempts", "question_patterns", "users"],
  "notes_column_exists": true,
  "level_column_exists": true,
  "prompts_table_exists": false,
  "prompts_indexes_exist": false,
  "needs_migration": true
}
```

#### Step 2: Apply All Migrations (Including Prompts Table)
Use the existing `/admin/apply-migrations` endpoint - it now includes prompts table creation:

```bash
curl -X POST "https://your-vercel-app.vercel.app/admin/apply-migrations?admin_key=YOUR_ADMIN_KEY"
```

**Expected Success Response:**
```json
{
  "success": true,
  "message": "All migrations applied successfully (including prompts table)",
  "migrations_applied": [
    "Base tables (attempts, question_patterns, users)",
    "Notes column on question_patterns",
    "Level column on question_patterns",
    "Prompts table with indexes",
    "Subscription column on users"
  ],
  "final_status": {
    "current_version": "007",
    "prompts_table_exists": true,
    "prompts_indexes_exist": true,
    "needs_migration": false
  }
}
```

#### Step 3: Verify Migration
```bash
curl -X GET "https://your-vercel-app.vercel.app/admin/migration-status?admin_key=YOUR_ADMIN_KEY"
```

**Expected Response After Migration:**
```json
{
  "current_version": "007",
  "alembic_table_exists": true,
  "existing_tables": ["attempts", "question_patterns", "users", "prompts"],
  "notes_column_exists": true,
  "level_column_exists": true,
  "prompts_table_exists": true,
  "prompts_indexes_exist": true,
  "needs_migration": false
}
```

---

### Option 2: Manual SQL Execution

If you prefer to run SQL directly on your Neon database:

#### Step 1: Connect to Your Neon Database
```bash
psql "postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

#### Step 2: Create the Prompts Table
```sql
-- Create the prompts table
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    uid TEXT NOT NULL,
    request_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    is_live INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_prompts_uid ON prompts(uid);
CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);

-- Update migration version
INSERT INTO alembic_version (version_num) VALUES ('007')
ON CONFLICT (version_num) DO NOTHING;
```

#### Step 3: Verify Tables
```sql
-- Check if prompts table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'prompts';

-- Check if indexes exist
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'prompts';

-- Check migration version
SELECT version_num FROM alembic_version ORDER BY version_num DESC;
```

**Expected Results:**
- Table: `prompts` should be listed
- Indexes: `idx_prompts_uid`, `idx_prompts_created_at` should be listed
- Version: Should show `007`

---

## Admin Key Setup

The admin endpoints require an admin key for security. Set this in your Vercel environment variables:

**Vercel Dashboard:**
1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add: `ADMIN_KEY` with a secure value (e.g., a UUID)
4. Redeploy your application

**Using Vercel CLI:**
```bash
vercel env add ADMIN_KEY
# Enter your secure admin key when prompted
```

---

## Testing the Migration

### Test 1: Generate Questions with Prompt Storage
```bash
curl -X POST "https://your-vercel-app.vercel.app/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "test_user_123",
    "level": 1,
    "is_live": 0
  }'
```

### Test 2: Verify Prompt Was Saved
Connect to your database and run:
```sql
SELECT id, uid, is_live, 
       LENGTH(request_text) as request_length,
       LENGTH(response_text) as response_length,
       created_at
FROM prompts
ORDER BY created_at DESC
LIMIT 5;
```

**Expected Output:**
```
 id  |      uid       | is_live | request_length | response_length |         created_at          
-----+----------------+---------+----------------+-----------------+-----------------------------
  1  | test_user_123  |    0    |       66       |       540       | 2025-10-21 10:30:45.123456
```

---

## Rollback Plan

If you need to rollback the migration:

```sql
-- Drop the prompts table
DROP TABLE IF EXISTS prompts;

-- Update migration version back to 006
UPDATE alembic_version SET version_num = '006' WHERE version_num = '007';
```

---

## Common Issues & Solutions

### Issue 1: "Table already exists" Error
**Solution:** The table already exists. Run the migration status endpoint to verify.

### Issue 2: "Invalid admin key" Error
**Solution:** Ensure `ADMIN_KEY` environment variable is set correctly in Vercel.

### Issue 3: Missing Indexes
**Solution:** Run the migration endpoint again - it will create missing indexes without recreating the table.

### Issue 4: Connection Timeout
**Solution:** Vercel functions have a 10-second timeout on Hobby plan. If migration takes too long, use manual SQL execution.

---

## Post-Migration Verification Checklist

- [ ] Prompts table exists in database
- [ ] Both indexes (`idx_prompts_uid`, `idx_prompts_created_at`) created
- [ ] Migration version updated to `007`
- [ ] Test `/generate-questions` endpoint saves prompts
- [ ] Verify prompts appear in database with correct structure
- [ ] Check that `is_live` flag works correctly
- [ ] Monitor application logs for any errors

---

## Support

If you encounter issues:

1. Check application logs in Vercel dashboard
2. Verify environment variables are set correctly
3. Test migration status endpoint first
4. Use manual SQL execution if API endpoints timeout

---

## Migration Timeline

**Estimated Time:** 2-5 minutes
- Status check: 10 seconds
- Migration execution: 30-60 seconds
- Verification: 1-2 minutes
- Testing: 2-3 minutes

---

## Next Steps After Migration

1. Monitor the prompts table for incoming data
2. Set up database backup schedule (if not already done)
3. Consider implementing prompt analytics dashboard
4. Review and optimize database performance if needed

---

**Migration Version:** 007  
**Table Added:** `prompts`  
**Indexes Added:** `idx_prompts_uid`, `idx_prompts_created_at`  
**Backward Compatible:** Yes ✅  
**Breaking Changes:** None ✅
