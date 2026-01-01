# # SmartBoy Backend Environment Manager (PowerShell)
# # Usage: .\start-dev.ps1

# Write-Host "🚀 Starting SmartBoy Backend in DEVELOPMENT mode..." -ForegroundColor Green
# Write-Host ""

# # Set environment to development
# $env:ENVIRONMENT = "development"

# # Copy development environment file
# if (Test-Path ".env.development") {
#     Copy-Item ".env.development" ".env" -Force
#     Write-Host "✅ Environment set to DEVELOPMENT" -ForegroundColor Green
#     Write-Host "💾 Database: PostgreSQL (localhost:5432/smartboy_dev)" -ForegroundColor Cyan
#     Write-Host "🌐 Server: http://localhost:8000" -ForegroundColor Cyan
#     Write-Host "🔄 Auto-reload: ENABLED" -ForegroundColor Cyan
# } else {
#     Write-Host "❌ .env.development file not found!" -ForegroundColor Red
#     exit 1
# }

# # Check if PostgreSQL is available for local development
# Write-Host ""
# Write-Host "🔍 Checking PostgreSQL setup..." -ForegroundColor Yellow

# try {
#     $pgVersion = & psql --version 2>$null
#     if ($LASTEXITCODE -eq 0) {
#         Write-Host "✅ PostgreSQL is installed: $pgVersion" -ForegroundColor Green
#     } else {
#         Write-Host "⚠️ PostgreSQL not found. Database auto-creation may not work." -ForegroundColor Yellow
#         Write-Host "💡 Run: .\setup-postgres.ps1 to set up PostgreSQL" -ForegroundColor Gray
#     }
# } catch {
#     Write-Host "⚠️ PostgreSQL not found in PATH. Auto-setup may fail." -ForegroundColor Yellow
#     Write-Host "💡 Run: .\setup-postgres.ps1 to set up PostgreSQL" -ForegroundColor Gray
# }

# # Check if service is running
# try {
#     $service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "Running" }
#     if ($service) {
#         Write-Host "✅ PostgreSQL service is running" -ForegroundColor Green
#     } else {
#         Write-Host "⚠️ PostgreSQL service not running. Starting may fail." -ForegroundColor Yellow
#         Write-Host "💡 Run: Start-Service postgresql* or .\setup-postgres.ps1" -ForegroundColor Gray
#     }
# } catch {
#     Write-Host "ℹ️ Could not check PostgreSQL service status" -ForegroundColor Blue
# }

# Write-Host ""
# Write-Host "📡 Starting development server..." -ForegroundColor Yellow
# Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
# Write-Host ""

# # Start the development server
# & python -m uvicorn app.main:app --host localhost --port 8000 --reload