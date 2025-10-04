# PostgreSQL Setup Script for SmartBoy Development
# Run as Administrator

Write-Host "🐘 Setting up PostgreSQL for SmartBoy Development..." -ForegroundColor Green
Write-Host ""

# Check if PostgreSQL is installed
try {
    $pgVersion = & psql --version 2>$null
    Write-Host "✅ PostgreSQL is installed: $pgVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ PostgreSQL not found. Please install PostgreSQL first:" -ForegroundColor Red
    Write-Host "   Download from: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "   OR use Chocolatey: choco install postgresql" -ForegroundColor Yellow
    exit 1
}

# Check if PostgreSQL service is running
$service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Host "✅ PostgreSQL service is running" -ForegroundColor Green
} else {
    Write-Host "⚠️ Starting PostgreSQL service..." -ForegroundColor Yellow
    Start-Service -Name "postgresql*" -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "🗄️ Creating development database and user..." -ForegroundColor Yellow

# Create SQL commands
$sqlCommands = @"
-- Create development user
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'smartboy_dev') THEN
        CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';
    END IF;
END
`$`$;

-- Create development database
SELECT 'CREATE DATABASE smartboy_dev OWNER smartboy_dev' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'smartboy_dev')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;
"@

# Save SQL to temporary file
$sqlFile = "$env:TEMP\smartboy_setup.sql"
$sqlCommands | Out-File -FilePath $sqlFile -Encoding UTF8

try {
    # Execute SQL commands
    Write-Host "📝 Executing database setup commands..." -ForegroundColor Blue
    & psql -U postgres -f $sqlFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database setup completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📊 Development database details:" -ForegroundColor Cyan
        Write-Host "   Host: localhost" -ForegroundColor White
        Write-Host "   Port: 5432" -ForegroundColor White
        Write-Host "   Database: smartboy_dev" -ForegroundColor White
        Write-Host "   Username: smartboy_dev" -ForegroundColor White
        Write-Host "   Password: smartboy_dev" -ForegroundColor White
        Write-Host ""
        Write-Host "🧪 Testing connection..." -ForegroundColor Yellow
        
        # Test connection
        & psql -h localhost -U smartboy_dev -d smartboy_dev -c "SELECT 1;" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Connection test successful!" -ForegroundColor Green
            Write-Host ""
            Write-Host "🚀 Ready to start development server!" -ForegroundColor Green
            Write-Host "   Run: .\start-dev.ps1" -ForegroundColor Yellow
        } else {
            Write-Host "⚠️ Connection test failed. You may need to configure PostgreSQL authentication." -ForegroundColor Yellow
            Write-Host "   Check pg_hba.conf for local connections" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ Database setup failed. Check PostgreSQL logs." -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ Error executing setup: $_" -ForegroundColor Red
    Write-Host "💡 Try running this manually:" -ForegroundColor Yellow
    Write-Host "   psql -U postgres" -ForegroundColor Gray
    Write-Host "   Then run the SQL commands from: $sqlFile" -ForegroundColor Gray
} finally {
    # Cleanup
    if (Test-Path $sqlFile) {
        Remove-Item $sqlFile -Force
    }
}

Write-Host ""
Write-Host "📚 For more help, see: POSTGRESQL_SETUP.md" -ForegroundColor Gray