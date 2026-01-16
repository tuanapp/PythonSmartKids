<#
.SYNOPSIS
    Quick diagnostic for Google Play service account configuration

.DESCRIPTION
    Decodes and displays service account information from GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
    environment variable to help troubleshoot 401 permission errors.

.EXAMPLE
    # Set environment variable from Vercel first
    $env:GOOGLE_PLAY_SERVICE_ACCOUNT_JSON = "YOUR_BASE64_STRING_FROM_VERCEL"
    .\check-service-account.ps1
#>

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Google Play Service Account Checker" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Check if environment variable exists
$encoded = $env:GOOGLE_PLAY_SERVICE_ACCOUNT_JSON

if (-not $encoded) {
    Write-Host "ERROR: GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "To use this tool:" -ForegroundColor Yellow
    Write-Host "1. Get the base64 string from Vercel Dashboard → Environment Variables"
    Write-Host "2. Set it temporarily:"
    Write-Host '   $env:GOOGLE_PLAY_SERVICE_ACCOUNT_JSON = "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAic21hcnRib3ktNDYwMDExIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiMWRkOGQ1YjlhMDMwZjljOTg4OTExOGQ2MTBkOTkzNTMwNzlmODM3ZiIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZRSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS2N3Z2dTakFnRUFBb0lCQVFESCtzZ3U4RDlXQkZUMVxuaE9oSGswYlBwTDIrMi9xam5mbmdVYm9peFRGcjdnNkxDLzN1UTlQNXIzM1c3MDdCZWtVUVRacmxHa2xNRXV4aFxuVGpqWXIwZmNhekFjV1VPd3VUckJnbTRNdVBESHRNUnJvVHJFckx4MnVLNWpmWnM5ZzZpUndLUzFHalNTbnFsWlxuemJZcGNUamg2S1lqTmV5aHgrOC9iZXh5T201N2hqWWRmSXVaMkJXRzREVkUzU2o5UFhVcDQxRFg1clYxSUtzaVxuZktmZFdZdmRrY1dGRjEwNFBodVdPSGw5dG5WMGp2SnR6MjFlOWNIVTV3MjhHOThEUFgvY0ZSd09Gdmptd3d1L1xua1A5YzllNWk3VDJXbHUrbDAxbWMzakFKdk0vSU14akh4djVMYzE4T3ZDK3dLLy91WDRncTljS1pUU3FrcElqdVxuOXRwR0ZOejlBZ01CQUFFQ2dnRUFVUThWZW5VMmJ3TFZmeWx1ejZoaVlRTkpTQ1k1aTMyYXpmTENySnBhcElGN1xua3AvN1AwdHVEankwbU4wcWdxRXhnbUM2Z3RmclV2TXVybWg3QVZYWEhvQ3lJU09MblFRUHpXVTFmMkd0YzMyUlxueW9DeFpnd1FYbDBRanRKWWpSQWpVV1VSUGpsUGl3alY0MGxQWjYvMW14aG0wMG5sejFQUDVkbUVLRzhIM25nNVxuckw1VmpiSVRhSGVJWHZBRHhPaHhyNCtwZzNnQ0daVUFaa0dheGVteTdhbkxOcWhjZzNWVzBUNUtPTllDQk9QNFxuNU1MYXJQKzg3bWZLQWRyd3BydnU5Qks2b2ZjSTJZQURUOWlGUDdROUY2cTR5czVCUWhBajBkNUhXZ2g1L3NRTVxuMTVsRW96Q3dJWG15YkpiV0xSVmlaY3BwdzhPVWt0Rm1tWDhXa2JwSGZ3S0JnUUQzTXFYcFFuaXd4TUEwek0weVxuWTRkYm0yc0x3Y2g1ME0wYU8zbndhaGRDN0Z1T0tSK2s3L2hRWitnMVZyU3Rnd001S3RXWEtwRzRCRXBoTk55cVxucmI2QWhWd1BSdVpSYXJ5blJ1NzRFWlc0Wkw5QkY0U25hN0NSUGVuWUc1TkpoREVBZmdNOTh1ZzU3aXNJMXdBMVxuWFB5ZjRZWmo0Zno4QXdEMWZkd2VwZ09DeHdLQmdRRFBHYlphTitIN2hkQWFpcjZnTENXcEpzTjNUdFlEWXJBNVxucHV1VC9IY0JWMXN2UmpzWmZLTGlPTlRKNXVqYUNhKzF4QmdGS3JKbGxmNUpneXFKdVp6OWt6eHp3YURBc0lPSFxubXA2QUhyZnNYaUxoVWVyTFV5QVpsZ09aOXQyeU1yTW9aazdqRHZlaVo5YW90VGtMVjk5a2VlYWtEQlRBdVNtMlxuaWx4cHA4ZGVHd0tCZ0JTbHRGbnhaV2RPWjhlQk83cHp1Y0NiRUt2Z3VjQURBcjZvTFIwNW4wdkZ0amYvazFjUlxuZkNvckk2Z2czK0tHU09TamdVZXBGSmJNTlBJOW1oamZma1A1MzZDZkNXblBnb1p1VkZPQUZJTmNWdVUyODZ1UVxuUVNWQWlLRzJXKzBPRDVHODlNUmQzNnZIQ3Uwb0dDcGM0L1R1djJ6a1dWOHJXUThvUGhTSlJVM05Bb0dCQUlsV1xuenRRVGZSeDB4K1hpSHJwUHJJWDVPK1R4OWdEMndGRHJQZ3k4ZnhyM21IUElTa2NEblcwU0xTTGJxNDEwb1A2VVxuVlMyUC9CQmNJTzhWT2U5dGxRdWdTWldtVVhtWFZSSm5XamN5cDl2ckxZeG82NkQ4dGl2aGpPL2NnM2E2SW85blxuRVdlSU5IYVNFQXQvYXAzNEh5QWRxdk1kUStIdXFSZnh0NGtsaDVRREFvR0FNK1FoT01NOHVKRjdTWjdoWHUrMVxuUmdPYlArZXBpaTZlNytDc3phMGlhUm50NWhKRS9UbjlaaVVRZHZ3VTZKODJKMVI0Zi91c3hmMTJiY3ZoaVFGU1xudHFEbnJvOFJ5bDNscTBHL2h0UXNqbGQ0TnEwVERmd3pHQ3VRcGVCWkd1eWpaSEdZNTRqM3JHckdvOURDY3JScFxuZjV2YzN4NGxCbm1FanJtVnZiRHkzeXM9XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAic21hcnRib3ktYmlsbGluZ0BzbWFydGJveS00NjAwMTEuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLAogICJjbGllbnRfaWQiOiAiMTA2NTMxNDM5NzM1MzE4MTEyMTk3IiwKICAiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLAogICJ0b2tlbl91cmkiOiAiaHR0cHM6Ly9vYXV0aDIuZ29vZ2xlYXBpcy5jb20vdG9rZW4iLAogICJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vb2F1dGgyL3YxL2NlcnRzIiwKICAiY2xpZW50X3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vcm9ib3QvdjEvbWV0YWRhdGEveDUwOS9zbWFydGJveS1iaWxsaW5nJTQwc21hcnRib3ktNDYwMDExLmlhbS5nc2VydmljZWFjY291bnQuY29tIiwKICAidW5pdmVyc2VfZG9tYWluIjogImdvb2dsZWFwaXMuY29tIgp9Cg=="'
    Write-Host "3. Run this script again"
    Write-Host ""
    exit 1
}

Write-Host "✓ Environment variable found" -ForegroundColor Green
Write-Host "  Length: $($encoded.Length) characters"
Write-Host ""

# Decode base64
try {
    Write-Host "Decoding base64..." -ForegroundColor Yellow
    
    # Add padding if needed
    $padding = $encoded.Length % 4
    if ($padding -gt 0) {
        $encoded += "=" * (4 - $padding)
    }
    
    $bytes = [System.Convert]::FromBase64String($encoded)
    $json = [System.Text.Encoding]::UTF8.GetString($bytes)
    $serviceAccount = $json | ConvertFrom-Json
    
    Write-Host "✓ Successfully decoded" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "ERROR: Failed to decode base64" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "- Incomplete copy from Vercel (ensure you got the full string)"
    Write-Host "- Extra spaces or newlines in the value"
    Write-Host "- Invalid base64 encoding"
    Write-Host ""
    exit 1
}

# Display service account info
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "SERVICE ACCOUNT INFORMATION" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Email:      " -NoNewline -ForegroundColor Yellow
Write-Host $serviceAccount.client_email -ForegroundColor White
Write-Host "Project ID: " -NoNewline -ForegroundColor Yellow
Write-Host $serviceAccount.project_id -ForegroundColor White
Write-Host "Client ID:  " -NoNewline -ForegroundColor Yellow
Write-Host $serviceAccount.client_id -ForegroundColor White
Write-Host "Key ID:     " -NoNewline -ForegroundColor Yellow
Write-Host $serviceAccount.private_key_id -ForegroundColor White
Write-Host ""

# Instructions
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "NEXT STEPS - GRANT PERMISSIONS IN GOOGLE PLAY CONSOLE" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Go to: https://play.google.com/console" -ForegroundColor Yellow
Write-Host "2. Select: SmartBoy app (tuanorg.smartboy)"
Write-Host "3. Navigate: Setup → API access"
Write-Host "4. Find this service account:"
Write-Host "   $($serviceAccount.client_email)" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Click the email and grant these permissions:" -ForegroundColor Yellow
Write-Host "   ✓ View app information and download bulk reports (read-only)" -ForegroundColor Green
Write-Host "   ✓ View financial data, orders, and cancellation survey responses" -ForegroundColor Green
Write-Host "   ✓ Manage orders and subscriptions" -ForegroundColor Green
Write-Host ""
Write-Host "6. Save and wait 15-30 minutes for propagation" -ForegroundColor Yellow
Write-Host ""
Write-Host "7. Redeploy backend to refresh credentials:" -ForegroundColor Yellow
Write-Host '   git commit --allow-empty -m "Refresh Google Play API credentials"'
Write-Host '   git push'
Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "For detailed fix instructions, see:" -ForegroundColor Yellow
Write-Host "  docs/GOOGLE_PLAY_401_QUICK_FIX.md"
Write-Host "  docs/GOOGLE_PLAY_API_PERMISSION_FIX.md"
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
