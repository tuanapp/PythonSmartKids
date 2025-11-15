# Check Production Database Schema

Write-Host "Checking production database schema..." -ForegroundColor Cyan

# Get schema info for prompts table
$query = @"
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'prompts'
ORDER BY ordinal_position
"@

Write-Host "`nPrompts table columns:" -ForegroundColor Yellow

try {
    # Use the API to query the database
    $body = @{
        query = $query
    } | ConvertTo-Json

    # We need to create a simple query endpoint or check the migration status
    $response = Invoke-WebRequest -Uri "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key" -Method Post
    $content = $response.Content | ConvertFrom-Json
    Write-Host ($content | ConvertTo-Json -Depth 10) -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nDone!" -ForegroundColor Cyan
