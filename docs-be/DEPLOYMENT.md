# Deployment Guide

*Last Updated: December 2025*

This guide covers deploying SmartBoy backend to Vercel with Neon PostgreSQL.

## Overview

- **Platform**: Vercel (serverless)
- **Database**: Neon PostgreSQL (cloud)
- **Auto-deploy**: On push to repository
- **Production URL**: https://python-smart-kids.vercel.app

---

## Quick Deployment

### Deploy Code
```bash
git push origin main
# Vercel auto-deploys on push
```

### Apply Database Migrations
```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

**That's it!** The single migration endpoint handles all database changes.

---

## Initial Setup

### 1. Install Vercel CLI

```bash
npm install -g vercel
vercel login
```

### 2. First Deployment

```bash
cd Backend_Python
vercel
```

Follow prompts:
- Set up and deploy: Yes
- Link to existing project: No (first time)
- Accept defaults for build settings

### 3. Configure Environment Variables

In Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_PROVIDER` | `neon` | Database type |
| `NEON_DBNAME` | `smartboydb` | Database name |
| `NEON_USER` | `tuanapp` | Database user |
| `NEON_PASSWORD` | `your-password` | Database password |
| `NEON_HOST` | `ep-xxx.aws.neon.tech` | Neon host |
| `NEON_SSLMODE` | `require` | SSL mode |
| `ADMIN_KEY` | `secure-random-key` | Admin API key |
| `FORGE_API_KEY` | `your-ai-key` | AI service key |
| `FORGE_BASE_URL` | `https://api.forge.tensorblock.co/v1` | AI base URL |
| `FORGE_AI_MODEL` | `Gemini/models/gemini-2.0-flash` | AI model |

### 4. Production Deploy

```bash
vercel --prod
```

### 5. Apply Migrations

```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

---

## Database Migrations

### Why Custom Migrations?

Vercel serverless has limitations:
- Read-only file system
- No persistent storage between function calls
- Cold starts don't run migration scripts

**Solution**: HTTP-based migration endpoints that run SQL directly.

### Migration Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/migration-status` | GET | Check current database state |
| `/admin/apply-migrations` | POST | Apply all pending migrations |

### Applying Migrations

```bash
# Check current status
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=YOUR_KEY"

# Apply all migrations
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

### Migration Features

- ✅ **Safe to run multiple times** - Idempotent operations
- ✅ **Handles all changes** - Tables, columns, indexes
- ✅ **Backward compatible** - Works on fresh or existing databases
- ✅ **Version tracking** - Uses alembic_version table

### Example Status Response

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

---

## Deployment Workflow

### Standard Deployment

1. **Make changes** locally and test
2. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin main
   ```
3. **Vercel auto-deploys** - Monitor at vercel.com
4. **Apply migrations** (if schema changed):
   ```bash
   curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
   ```
5. **Verify** the deployment

### Feature Branch Deployment

```bash
# Push feature branch
git push origin feature/my-feature

# Vercel creates preview deployment
# Test at: your-project-git-feature-my-feature.vercel.app
```

---

## Vercel Configuration

### `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### `.vercelignore`

```
.git
.env
.env.*
__pycache__
*.pyc
tests/
docs/
*.md
```

---

## Monitoring

### Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. View:
   - **Deployments** - Deploy history and status
   - **Functions** - Serverless function logs
   - **Analytics** - Traffic and performance

### Application Logs

In Vercel Dashboard → Project → Functions → Select function → View logs

### Health Check

```bash
# Check if API is responding
curl "https://python-smart-kids.vercel.app/"

# Check database connection
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=YOUR_KEY"
```

---

## Troubleshooting

### Cold Starts

**Issue**: First request after idle period is slow

**Solution**: Normal for serverless. Consider:
- Keeping functions warm with scheduled pings
- Upgrading Vercel plan for faster cold starts

### Function Timeout

**Issue**: Request times out (10s free tier, 60s paid)

**Solution**:
- Optimize slow database queries
- For migrations, run again (they're idempotent)
- Consider breaking large operations into smaller chunks

### Database Connection Issues

**Issue**: Can't connect to database

**Check**:
1. Environment variables are set correctly
2. Neon database is in active state (not paused)
3. SSL mode is `require` for production

```bash
# Verify env vars
curl "https://python-smart-kids.vercel.app/admin/migration-status?admin_key=YOUR_KEY"
```

### Migration Failures

**Issue**: Migration doesn't complete

**Solution**:
1. Check error message in response
2. Run migration again (safe - idempotent)
3. Check Neon dashboard for database status

### Environment Variable Issues

**Issue**: App can't find configuration

**Check**:
1. Variables set in Vercel dashboard
2. Deployed after setting variables
3. Variable names match exactly (case-sensitive)

---

## Security

### Admin Key

1. Use a strong, random admin key in production
2. Never commit admin key to repository
3. Set via Vercel environment variables only

### Database Credentials

1. Never commit database passwords
2. Use Vercel environment variables
3. Rotate credentials periodically

### HTTPS

- Vercel provides automatic HTTPS
- All API endpoints use HTTPS in production

---

## Scaling

### Free Tier Limits

- 10-second function timeout
- 100GB bandwidth/month
- Limited serverless function invocations

### Upgrading

For higher limits:
1. Upgrade Vercel plan
2. Upgrade Neon database plan (more connections, compute)

### Performance Tips

1. **Optimize queries** - Use indexes, limit result sets
2. **Connection pooling** - Neon handles this automatically
3. **Caching** - Consider caching for frequently accessed data

---

## Rollback

### Vercel Rollback

1. Go to Vercel Dashboard → Deployments
2. Find previous working deployment
3. Click "..." → "Promote to Production"

### Database Rollback

Neon provides point-in-time recovery:
1. Go to Neon Dashboard
2. Branches → Create branch from past point
3. Point application to recovery branch

---

## Checklist

### Before Deployment
- [ ] Tests pass locally
- [ ] Environment variables configured
- [ ] Database migrations tested locally

### After Deployment
- [ ] Health check passes
- [ ] Database migrations applied
- [ ] Critical endpoints tested
- [ ] Logs show no errors

---

*For database-specific information, see [DATABASE.md](DATABASE.md)*
*For local development setup, see [DEVELOPMENT.md](DEVELOPMENT.md)*
