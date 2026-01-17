# Firebase FCM Setup Script
# This script helps you set up Firebase Cloud Messaging for push notifications

Write-Host "Firebase FCM Setup for SmartBoy" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Download Firebase Service Account Key" -ForegroundColor Yellow
Write-Host "   1. Go to: https://console.firebase.google.com/" -ForegroundColor Gray
Write-Host "   2. Select your project: smartboy-48e6c" -ForegroundColor Gray
Write-Host "   3. Go to Project Settings (gear icon) > Service Accounts" -ForegroundColor Gray
Write-Host "   4. Click 'Generate new private key'" -ForegroundColor Gray
Write-Host "   5. Save the JSON file as 'firebase-service-account.json' in Backend_Python/" -ForegroundColor Gray
Write-Host ""

$serviceAccountPath = Join-Path $PSScriptRoot "firebase-service-account.json"

if (-Not (Test-Path $serviceAccountPath)) {
    Write-Host "ERROR: firebase-service-account.json not found!" -ForegroundColor Red
    Write-Host "   Please download it from Firebase Console and place it at:" -ForegroundColor Gray
    Write-Host "   $serviceAccountPath" -ForegroundColor White
    Write-Host ""
    Write-Host "   Then run this script again." -ForegroundColor Gray
    exit 1
}

Write-Host "SUCCESS: Found firebase-service-account.json" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Encode service account to Base64" -ForegroundColor Yellow
$serviceAccountJson = Get-Content $serviceAccountPath -Raw
$serviceAccountBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($serviceAccountJson))

Write-Host "SUCCESS: Service account encoded successfully" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Update environment files" -ForegroundColor Yellow

# Update .env.production
$envProdPath = Join-Path $PSScriptRoot ".env.production"
if (Test-Path $envProdPath) {
    $content = Get-Content $envProdPath -Raw
    
    # Remove existing FIREBASE_SERVICE_ACCOUNT_JSON if present
    $content = $content -replace "(?m)^FIREBASE_SERVICE_ACCOUNT_JSON=.*`r?`n?", ""
    
    # Add new FIREBASE_SERVICE_ACCOUNT_JSON at the end
    $content = $content.TrimEnd() + "`r`n`r`n# Firebase Cloud Messaging (FCM) for push notifications`r`nFIREBASE_SERVICE_ACCOUNT_JSON=$serviceAccountBase64`r`n"
    
    Set-Content -Path $envProdPath -Value $content -NoNewline
    Write-Host "   SUCCESS: Updated .env.production" -ForegroundColor Green
} else {
    Write-Host "   ERROR: .env.production not found" -ForegroundColor Red
}

# Update .env.development
$envDevPath = Join-Path $PSScriptRoot ".env.development"
if (Test-Path $envDevPath) {
    $content = Get-Content $envDevPath -Raw
    
    # Remove existing FIREBASE_SERVICE_ACCOUNT_JSON if present
    $content = $content -replace "(?m)^FIREBASE_SERVICE_ACCOUNT_JSON=.*`r?`n?", ""
    
    # Add new FIREBASE_SERVICE_ACCOUNT_JSON at the end
    $content = $content.TrimEnd() + "`r`n`r`n# Firebase Cloud Messaging (FCM) for push notifications`r`nFIREBASE_SERVICE_ACCOUNT_JSON=$serviceAccountBase64`r`n"
    
    Set-Content -Path $envDevPath -Value $content -NoNewline
    Write-Host "   SUCCESS: Updated .env.development" -ForegroundColor Green
} else {
    Write-Host "   ERROR: .env.development not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "Firebase FCM setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "   1. Apply database migration:" -ForegroundColor Gray
Write-Host "      https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=dev-admin-key" -ForegroundColor White
Write-Host ""
Write-Host "   2. Restart your backend server" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Test FCM notifications" -ForegroundColor Gray
Write-Host ""
