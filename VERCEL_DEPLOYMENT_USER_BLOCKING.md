# User Blocking System - Vercel Deployment Guide

## What Was Changed

### 1. Database Migration System Updated
**File**: `Backend_Python/app/db/vercel_migrations.py`

**Changes**:
- Updated `check_migration_status()` to check for user blocking fields
- Added `add_user_blocking_migration()` method to handle blocking fields migration
- Updated `apply_all_migrations()` to include user blocking migration
- Changed migration version from '007' to '008'

**New migration includes**:
- Adds `is_blocked`, `blocked_reason`, `blocked_at`, `blocked_by` columns to `users` table
- Creates `user_blocking_history` table with all necessary columns
- Creates performance indexes on blocking fields

### 2. Backend Services & APIs
**Files added/modified**:
- `app/services/user_blocking_service.py` - New service for blocking operations
- `app/db/models.py` - Added User and UserBlockingHistory models
- `app/api/routes.py` - Added blocking endpoints
- `app/middleware/user_blocking_middleware.py` - New middleware for automatic blocking checks
- `app/main.py` - Integrated blocking middleware

### 3. Frontend Integration
**Files modified**:
- `Frontend_Capacitor/android/app/src/main/assets/public/js/apiHelper.js` - Added checkUserStatus()
- `Frontend_Capacitor/android/app/src/main/assets/public/js/mathQuestions.js` - Added blocking checks and popup

## Deployment Steps

### Step 1: Commit and Push Changes ✅

```bash
cd d:\private\GIT\SmartBoy
git add .
git commit -m "feat: Add user blocking system with migration support"
git push origin 002-currently-only-a
```

### Step 2: Deploy to Vercel

Vercel will automatically deploy when you push to the repository.

**Monitor deployment**: https://vercel.com/tuanapp/python-smart-kids

### Step 3: Run Migration on Vercel Production Database

After Vercel deployment completes, run the migration endpoint:

```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "All migrations applied successfully (including user blocking)",
  "final_status": {
    "current_version": "008",
    "user_blocking_exists": true,
    "user_blocking_history_exists": true,
    "needs_migration": false
  },
  "migrations_applied": [
    "Base tables (attempts, question_patterns, users)",
    "Notes column on question_patterns",
    "Level column on question_patterns",
    "Prompts table with indexes",
    "Subscription column on users",
    "User blocking fields on users",
    "User blocking history table"
  ]
}
```

### Step 4: Verify Migration Status

```bash
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=dev-admin-key"
```

**Expected Response**:
```json
{
  "current_version": "008",
  "alembic_table_exists": true,
  "user_blocking_exists": true,
  "user_blocking_history_exists": true,
  "needs_migration": false
}
```

### Step 5: Test Blocking Endpoints

**Check user status** (public endpoint):
```bash
curl "https://python-smart-kids.vercel.app/users/TEST_UID/status"
```

**Block a user** (admin endpoint):
```bash
curl -X POST "https://python-smart-kids.vercel.app/users/TEST_UID/block" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Test blocking",
    "blocked_by": "admin",
    "admin_key": "dev-admin-key"
  }'
```

**Unblock a user** (admin endpoint):
```bash
curl -X POST "https://python-smart-kids.vercel.app/users/TEST_UID/unblock" \
  -H "Content-Type: application/json" \
  -d '{
    "unblocked_by": "admin",
    "admin_key": "dev-admin-key"
  }'
```

### Step 6: Update Frontend (Capacitor App)

After backend is deployed and tested:

1. Build the Android app with updated frontend code
2. Test the blocking flow on mobile device
3. Verify blocking popup appears correctly
4. Test WhatsApp support contact button

## Rollback Plan (if needed)

If there are issues with the migration:

1. **Revert database changes** (if necessary):
   ```sql
   -- Remove blocking fields from users table
   ALTER TABLE users DROP COLUMN IF EXISTS is_blocked;
   ALTER TABLE users DROP COLUMN IF EXISTS blocked_reason;
   ALTER TABLE users DROP COLUMN IF EXISTS blocked_at;
   ALTER TABLE users DROP COLUMN IF EXISTS blocked_by;
   
   -- Drop blocking history table
   DROP TABLE IF EXISTS user_blocking_history;
   
   -- Revert migration version
   DELETE FROM alembic_version WHERE version_num = '008';
   ```

2. **Revert code changes**:
   ```bash
   git revert <commit-hash>
   git push origin 002-currently-only-a
   ```

## Production Environment Variables

Make sure these are set in Vercel:

- `ADMIN_KEY` - Set to a secure value (not "dev-admin-key")
- `NEON_DBNAME` - Database name
- `NEON_USER` - Database user
- `NEON_PASSWORD` - Database password
- `NEON_HOST` - Database host

## Monitoring

After deployment, monitor:

1. **Vercel Logs**: Check for any errors in the deployment logs
2. **Database Performance**: Monitor query performance with new indexes
3. **API Response Times**: Check if middleware affects performance
4. **Error Rates**: Watch for any 403 errors or blocking-related issues

## Testing Checklist

- [ ] Migration applies successfully on Vercel
- [ ] User status check endpoint works
- [ ] Block user endpoint works (with admin key)
- [ ] Unblock user endpoint works (with admin key)
- [ ] Blocking history endpoint works (with admin key)
- [ ] Middleware blocks requests from blocked users
- [ ] Frontend shows blocking popup correctly
- [ ] WhatsApp support button works
- [ ] Session clears when user is blocked
- [ ] No errors in Vercel logs

## Success Criteria

✅ Migration version is '008'
✅ User blocking fields exist in users table
✅ User blocking history table exists
✅ All indexes are created
✅ API endpoints respond correctly
✅ Middleware blocks access for blocked users
✅ Frontend shows appropriate messages
✅ No performance degradation

## Support

If issues occur:
1. Check Vercel deployment logs
2. Check database connection and migration status
3. Test endpoints with curl commands above
4. Review USER_BLOCKING_SYSTEM.md for troubleshooting

## Notes

- The migration is idempotent - safe to run multiple times
- Existing data is preserved during migration
- New fields have sensible defaults (is_blocked = FALSE)
- System fails open if blocking check fails (better UX)
