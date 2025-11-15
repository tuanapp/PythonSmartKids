# Test Production Question Generation

Write-Host "Testing question generation on production..." -ForegroundColor Cyan

# Test 1: Generate questions
$body = @{
    uid = "5NZJhogMvocs6cmwq8IfBupiHtw1"
    is_live = $false
} | ConvertTo-Json

Write-Host "`nTest 1: Generating questions..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://python-smart-kids.vercel.app/generate-questions/" -Method Post -Body $body -ContentType "application/json"
    $content = $response.Content | ConvertFrom-Json
    Write-Host "Success! Generated questions" -ForegroundColor Green
    Write-Host "Daily count: $($content.daily_count)" -ForegroundColor Green
    Write-Host "Questions count: $($content.questions.Count)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# Test 2: Generate again to test increment
Write-Host "`nTest 2: Generating questions again (should increment count)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://python-smart-kids.vercel.app/generate-questions/" -Method Post -Body $body -ContentType "application/json"
    $content = $response.Content | ConvertFrom-Json
    Write-Host "Success! Generated questions" -ForegroundColor Green
    Write-Host "Daily count: $($content.daily_count)" -ForegroundColor Green
    Write-Host "Questions count: $($content.questions.Count)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host "`nDone!" -ForegroundColor Cyan
