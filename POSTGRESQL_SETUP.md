# PostgreSQL Setup for SmartBoy Development

## 🐘 PostgreSQL Installation & Setup

### 1. Install PostgreSQL

**Windows:**
- Download from: https://www.postgresql.org/download/windows/
- OR use Chocolatey: `choco install postgresql`
- OR use Scoop: `scoop install postgresql`

**macOS:**
- Use Homebrew: `brew install postgresql`
- OR use Postgres.app: https://postgresapp.com/

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### 2. Setup Development Database

**Option A: Using psql command line**
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create development user
CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';

-- Create development database
CREATE DATABASE smartboy_dev OWNER smartboy_dev;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;

-- Exit psql
\q
```

**Option B: Using PowerShell script (Windows)**
```powershell
# Run this in PowerShell as Administrator
.\setup-postgres.ps1
```

**Option C: Using pgAdmin**
1. Open pgAdmin
2. Create new database: `smartboy_dev`
3. Create new user: `smartboy_dev` with password `smartboy_dev`
4. Assign owner privileges to the user

### 3. Verify Connection

Test the connection:
```bash
psql -h localhost -U smartboy_dev -d smartboy_dev
```

Default connection details for development:
- **Host:** localhost
- **Port:** 5432
- **Database:** smartboy_dev
- **Username:** smartboy_dev
- **Password:** smartboy_dev

### 4. Start Development Server

Once PostgreSQL is set up:
```powershell
.\start-dev.ps1
```

## 🔧 Configuration

The development environment uses these PostgreSQL settings:
- **Connection String:** `postgresql://smartboy_dev:smartboy_dev@localhost:5432/smartboy_dev`
- **SSL Mode:** Disabled (local development)
- **Auto-create tables:** Yes (handled by the application)

## 🆘 Troubleshooting

**Connection refused?**
- Make sure PostgreSQL service is running
- Check if port 5432 is available
- Verify user and database exist

**Authentication failed?**
- Double-check username/password
- Ensure user has proper privileges
- Try connecting with psql first

**Database doesn't exist?**
- Run the database creation commands above
- Verify database name spelling

**Tables not created?**
- The application will create tables automatically on first run
- Check application logs for any errors

## 🚀 Quick Setup Script

Run this PowerShell script to automate the setup: