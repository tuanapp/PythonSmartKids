# Quick PostgreSQL Setup for SmartBoy

If you encounter authentication issues with the automatic setup, follow these manual steps:

## Option 1: Create Database Manually (Recommended)

1. **Open PostgreSQL Command Line (SQL Shell - psql)**
   - Start Menu → PostgreSQL → SQL Shell (psql)
   - Or open Command Prompt and run: `psql -U postgres`

2. **Create the development database and user:**
   ```sql
   -- Create the database
   CREATE DATABASE smartboy_dev;
   
   -- Create the user with password
   CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';
   
   -- Grant all privileges on the database
   GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;
   
   -- Grant create privileges on the schema
   \c smartboy_dev
   GRANT ALL ON SCHEMA public TO smartboy_dev;
   
   -- Exit
   \q
   ```

3. **Test the connection:**
   ```bash
   psql -h localhost -U smartboy_dev -d smartboy_dev -c "SELECT 1;"
   ```

## Option 2: Use pgAdmin (GUI)

1. **Open pgAdmin**
2. **Connect to PostgreSQL server**
3. **Create Database:**
   - Right-click "Databases" → Create → Database
   - Name: `smartboy_dev`
   - Owner: `postgres` (for now)
4. **Create User:**
   - Right-click "Login/Group Roles" → Create → Login/Group Role
   - General tab: Name = `smartboy_dev`
   - Definition tab: Password = `smartboy_dev`
   - Privileges tab: Check "Can login?"
5. **Grant Permissions:**
   - Right-click `smartboy_dev` database → Properties
   - Security tab → Add → smartboy_dev user with all privileges

## Option 3: Alternative Authentication

If you want to avoid passwords for local development, modify PostgreSQL's authentication:

1. **Find pg_hba.conf file** (usually in PostgreSQL installation data directory)
2. **Add this line for local development:**
   ```
   host    smartboy_dev    smartboy_dev    127.0.0.1/32    trust
   ```
3. **Restart PostgreSQL service**

## Verification

After setup, verify everything works:
```powershell
# Test connection
psql -h localhost -U smartboy_dev -d smartboy_dev -c "SELECT current_database(), current_user;"

# Should output:
# current_database | current_user
# smartboy_dev     | smartboy_dev
```

## Start Development Server

Once the database is set up, start the server:
```powershell
.\start-dev.ps1
```

The application will automatically create all required tables (users, attempts, question_patterns) when it starts.