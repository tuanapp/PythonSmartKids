# Vercel Database Migration Guide

## Quick Migration (All Database Changes)

To apply all database migrations to your Vercel production database, simply run:

```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key"
```

**That's it!** This endpoint handles ALL database migrations including:
- Base tables (attempts, question_patterns, users)
- Schema updates (notes column, level column, subscription column)
- New tables (prompts table with indexes)
- Any future migrations

---

## How It Works

The `/admin/apply-migrations` endpoint:
1. Checks current database state
2. Creates missing tables
3. Adds missing columns to existing tables
4. Creates necessary indexes
5. Updates migration version tracking

**Key Features:**
- ✅ **Safe to run multiple times** - Won't recreate existing objects
- ✅ **Idempotent** - Same result no matter how many times you run it
- ✅ **Handles all migrations** - No need for separate endpoints
- ✅ **Backward compatible** - Works on fresh or existing databases

---

## Verification

### Check Migration Status
```bash
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=dev-admin-key"
```

**Example Response:**
```json
{
  "current_version": "007",
  "alembic_table_exists": true,
  "existing_tables": ["attempts", "question_patterns", "users", "prompts"],
  "notes_column_exists": true,
  "level_column_exists": true,
  "subscription_column_exists": true,
  "prompts_table_exists": true,
  "prompts_indexes_exist": true,
  "needs_migration": false
}
```

---

## Admin Key Configuration

The admin endpoints require an admin key for security.

**For Production:**
Set `ADMIN_KEY` in your Vercel environment variables:

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add: `ADMIN_KEY` = `your-secure-key`
3. Redeploy your application

**For Development:**
The default admin key is `dev-admin-key` (configured in config.py)

---

## When to Run Migrations

Run the migration endpoint:
- ✅ After deploying code with new database schema changes
- ✅ When setting up a new environment
- ✅ After cloning the database to a new instance
- ✅ When migration status shows `needs_migration: true`

---

## Troubleshooting

### Issue: "Invalid admin key"
**Solution:** Verify `ADMIN_KEY` environment variable is set correctly in Vercel

### Issue: "Connection timeout"
**Solution:** Vercel functions timeout after 10 seconds on free tier. If migration times out, run it again - it's safe and will pick up where it left off

### Issue: "Table already exists"
**Solution:** This is normal - the migration is idempotent and skips existing objects

---

## Database Schema Overview

### Current Tables (as of Migration 007):

**attempts** - Stores student question attempts
**question_patterns** - Stores AI-generated question patterns  
**users** - User authentication and subscription data
**prompts** - Stores AI prompt requests/responses

### Migration History:
- 001-003: Base tables and initial schema
- 004: Notes column on question_patterns
- 005: Level column on question_patterns
- 006: Subscription column on users
- 007: Prompts table with indexes

---

## Manual Database Access (Optional)

If you need direct database access for debugging:

```bash
psql "postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
```

Then you can run SQL queries directly:
```sql
-- View all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Check migration version
SELECT version_num FROM alembic_version;

-- View prompts table
SELECT * FROM prompts ORDER BY created_at DESC LIMIT 10;
```

---

## Support

For issues or questions:
1. Check Vercel application logs
2. Verify environment variables
3. Test with `/admin/migration-status` endpoint first
4. Review this guide for troubleshooting steps

---

---

## What's Changed (Documentation Cleanup)

This guide replaces several outdated migration documents:
- ❌ Removed: `VERCEL_MIGRATION_007_PROMPTS.md` (too detailed, feature-specific)
- ❌ Removed: `VERCEL_MIGRATION_ISSUES.md` (outdated troubleshooting)
- ❌ Removed: `NOTES_COLUMN_CHANGES.md` (superseded by unified migration)
- ❌ Removed: `LEVEL_COLUMN_CHANGES.md` (superseded by unified migration)
- ❌ Removed: `TEST_MIGRATION_COMPLETE.md` (no longer relevant)
- ✅ Added: This unified migration guide

**Removed Unnecessary Endpoints:**
- ❌ `/admin/add-notes-column` (handled by apply-migrations)
- ❌ `/admin/add-level-column` (handled by apply-migrations)
- ❌ `/admin/add-prompts-table` (handled by apply-migrations)

**Kept Essential Endpoints:**
- ✅ `/admin/apply-migrations` - Single endpoint for all migrations
- ✅ `/admin/migration-status` - Check current state

---

**Last Updated:** October 2025  
**Current Migration Version:** 007  
**Endpoint:** `/admin/apply-migrations`  
**Status Endpoint:** `/admin/migration-status`
