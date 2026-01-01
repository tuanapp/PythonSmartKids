# SmartBoy Backend Environment Manager (PowerShell)
# Usage: .\start-prod.ps1

Write-Host "🏭 Starting SmartBoy Backend in PRODUCTION mode..." -ForegroundColor Red
Write-Host ""

# Set environment to production
$env:ENVIRONMENT = "production"

# Copy production environment file
if (Test-Path ".env.production") {
    Copy-Item ".env.production" ".env" -Force
    Write-Host "✅ Environment set to PRODUCTION" -ForegroundColor Green
    Write-Host "💾 Database: Neon PostgreSQL (cloud)" -ForegroundColor Cyan
    Write-Host "🌐 Server: http://0.0.0.0:8000" -ForegroundColor Cyan
    Write-Host "⚠️ Auto-reload: DISABLED" -ForegroundColor Yellow
} else {
    Write-Host "❌ .env.production file not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📡 Starting production server..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Start the production server
& python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# --reload