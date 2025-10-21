# Deploying PythonSmartKids to Vercel

This guide will walk you through deploying the PythonSmartKids project to Vercel.

## Prerequisites

1. A [Vercel account](https://vercel.com/signup)
2. [Node.js](https://nodejs.org/) installed (for Vercel CLI)
3. Your Neon PostgreSQL database credentials

## Deployment Steps

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Deploy the Project

Navigate to your project directory and run:

```bash
vercel
```

During the deployment process, you'll be asked a few questions:
- Set up and deploy: Yes
- Link to existing project: No (for first deployment)
- Project name: Choose a name or accept the default
- Directory: Press enter to use the current directory
- Build settings: Accept the defaults as they're set in vercel.json

### 4. Configure Environment Variables

After initial deployment, you need to set up your environment variables in Vercel:

1. Go to the [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to Settings → Environment Variables
4. Add the following variables:

```
DATABASE_PROVIDER = neon
NEON_DBNAME = smartboydb
NEON_USER = tuanapp
NEON_PASSWORD = HdzrNIKh5mM1
NEON_HOST = ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech
NEON_SSLMODE = require
ADMIN_KEY = your-secure-admin-key-for-migrations
AI_BRIDGE_API_KEY = your-ai-api-key
AI_BRIDGE_BASE_URL = your-ai-base-url
AI_BRIDGE_MODEL = your-ai-model
HTTP_REFERER = your-app-domain
APP_TITLE = PythonSmartKids
```

5. Click "Save" to apply the environment variables

### 5. Run Database Migrations

After deployment, run database migrations using the admin endpoint:

```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key"
```

**That's it!** This single command handles all database migrations.

📚 **For detailed migration documentation, see:** [`VERCEL_DATABASE_MIGRATION.md`](VERCEL_DATABASE_MIGRATION.md)

### 6. Redeploy with Environment Variables

```bash
vercel --prod
```

## Database Migrations in Vercel

### Why Traditional Migrations Don't Work

Vercel serverless functions have limitations that prevent traditional Alembic migrations:
- Read-only file system
- No persistent storage between function calls
- Cold starts don't run migration scripts

### Migration Solution

The application includes a Vercel-compatible migration system:

1. **Enhanced Database Initialization**: The `init_db()` method now creates all tables with the latest schema
2. **Migration API Endpoints**: Manual migration triggers via API calls
3. **Smart Schema Updates**: Detects existing schema and applies only necessary changes

### Available Migration Endpoints

All endpoints require an `admin_key` parameter for security:

- **`GET /admin/migration-status`**: Check current migration status
- **`POST /admin/apply-migrations`**: Apply all pending migrations  
- **`POST /admin/add-notes-column`**: Specifically add the notes column

### Example Migration Workflow

1. Deploy to Vercel
2. Check status: `GET /admin/migration-status?admin_key=YOUR_KEY`
3. Apply migrations: `POST /admin/apply-migrations?admin_key=YOUR_KEY`
4. Verify: Check status again to confirm completion

## Troubleshooting

### Cold Starts

Vercel functions have cold starts. The first request after a period of inactivity may be slow.

### Function Timeout

Functions on Vercel have execution time limits (10-60 seconds depending on your plan). Ensure that your API endpoints can complete within this timeframe.

### Database Connection

If you experience database connection issues:
1. Check that your environment variables are correctly set
2. Verify that your Neon database allows connections from Vercel's IP ranges
3. Ensure your database is in an active state

## Monitoring and Logs

1. Go to the [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Click on "Functions" to see your deployed serverless functions
4. Click on any function to see logs and performance metrics

## Scaling

The free tier of Vercel has certain limitations. If you need more:
- Upgrade to a paid plan for increased execution time and bandwidth
- Consider using a paid Neon PostgreSQL plan for higher connection limits and performance