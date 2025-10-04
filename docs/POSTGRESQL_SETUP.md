# PostgreSQL Development Setup Guide

This guide explains how to set up local PostgreSQL for SmartBoy development.

## Automatic Database Creation

The SmartBoy application now automatically creates the PostgreSQL database if it doesn't exist. This happens when:

1. You're using `localhost` as the database host (development environment)
2. The target database doesn't exist
3. The application has appropriate permissions

## Manual Setup (If Needed)

### 1. Install PostgreSQL

**Option A - Using winget (Windows 10+):**
```powershell
winget install PostgreSQL.PostgreSQL
```

**Option B - Using Chocolatey:**
```powershell
choco install postgresql
```

**Option C - Download Installer:**
Visit https://www.postgresql.org/download/windows/ and download the installer.

### 2. Start PostgreSQL Service

After installation, ensure PostgreSQL is running:
```powershell
# Check service status
Get-Service -Name "postgresql*"

# Start service if not running
Start-Service -Name "postgresql*"
```

### 3. Run Setup Script

Use the provided setup script to create the development database:
```powershell
.\setup-postgres.ps1
```

This script will:
- ✅ Check if PostgreSQL is installed and running
- 🗄️ Create the `smartboy_dev` database
- 👤 Create the `smartboy_dev` user with password `smartboy_dev`
- 🔑 Grant appropriate permissions
- 🧪 Test the connection

## Environment Configuration

### Development Environment (.env.development)
```bash
# Database Configuration - Use local PostgreSQL for development
DATABASE_PROVIDER=neon
DATABASE_URL=postgresql://smartboy_dev:smartboy_dev@localhost:5432/smartboy_dev

# Local PostgreSQL settings for development
NEON_DBNAME=smartboy_dev
NEON_USER=smartboy_dev
NEON_PASSWORD=smartboy_dev
NEON_HOST=localhost
NEON_SSLMODE=disable
```

### Production Environment (.env.production)
Uses Neon PostgreSQL cloud database - no local setup needed.

## Automatic Database Creation Flow

When you start the development server, the application will:

1. **Check if database exists**: Try to connect to `smartboy_dev` database
2. **Create database if needed**: If database doesn't exist, connect to default `postgres` database and create it
3. **Initialize schema**: Create all required tables (`attempts`, `users`, `question_patterns`)
4. **Ready to use**: Application starts normally

### Error Handling

If automatic database creation fails, you'll see warnings but the application will attempt to continue. Common issues:

- **Authentication failed**: Check if postgres user exists and has correct password
- **Permission denied**: User may not have CREATEDB privileges  
- **Service not running**: PostgreSQL service needs to be started

## Starting Development Server

### Automatic (Recommended)
```powershell
.\start-dev.ps1
```

### Manual
```powershell
# Set environment to development
$env:ENVIRONMENT = "development"

# Start server
cd Backend_Python
Scripts\python.exe -m uvicorn app.main:app --host localhost --port 8000 --reload
```

## Troubleshooting

### Database Connection Issues

**Problem**: `psycopg2.OperationalError: FATAL: database "smartboy_dev" does not exist`

**Solution**: The app should auto-create this, but if it fails:
```powershell
# Run setup script manually
.\setup-postgres.ps1

# Or create manually
psql -U postgres -c "CREATE DATABASE smartboy_dev;"
psql -U postgres -c "CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;"
```

**Problem**: `psycopg2.OperationalError: FATAL: password authentication failed`

**Solution**: Check pg_hba.conf file and ensure local connections are allowed:
```
# Add this line to pg_hba.conf
local   all             all                                     md5
```

**Problem**: `psql: command not found`

**Solution**: Add PostgreSQL to your PATH:
1. Find PostgreSQL installation directory (usually `C:\Program Files\PostgreSQL\16\bin`)
2. Add to System PATH environment variable
3. Restart PowerShell

### Service Issues

**Problem**: PostgreSQL service won't start

**Solution**: 
```powershell
# Check service status
Get-Service postgresql*

# Try to start service
Start-Service postgresql-x64-16

# If that fails, check Windows Services app
services.msc
```

## Database Schema

The application automatically creates these tables:

### `attempts` table
Stores student attempt history for math problems.

### `users` table  
Stores user registration information including:
- uid (Firebase UID)
- email
- name
- display_name
- grade_level (4, 5, 6, 7)
- registration_date

### `question_patterns` table
Stores question patterns and templates.

## Switching Between Environments

Use the environment manager to switch between development and production:

```powershell
# Switch to development (local PostgreSQL)
.\start-dev.ps1

# Switch to production (Neon PostgreSQL)  
.\start-prod.ps1
```

## Data Persistence

- **Development**: Data stored in local PostgreSQL database
- **Production**: Data stored in Neon PostgreSQL cloud database
- **Database files**: PostgreSQL data directory (usually in `%PROGRAMDATA%\PostgreSQL`)

## Security Notes

For development only:
- Default username/password: `smartboy_dev`/`smartboy_dev`
- SSL disabled for local connections
- Database accessible only from localhost

Production uses encrypted connections and secure credentials stored in environment variables.