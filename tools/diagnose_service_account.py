"""
Google Play Service Account Diagnostic Tool
Verifies service account configuration for billing API
"""
import os
import sys
import json
import base64
from pathlib import Path

def decode_service_account(encoded_json: str) -> dict:
    """Decode base64-encoded service account JSON"""
    try:
        # Add padding if needed
        encoded = encoded_json.strip()
        padding_needed = len(encoded) % 4
        if padding_needed:
            encoded += '=' * (4 - padding_needed)
        
        # Decode
        decoded = base64.b64decode(encoded).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        print(f"❌ Error decoding service account: {e}")
        return None

def validate_service_account(sa_info: dict) -> list:
    """Validate service account structure"""
    required_fields = [
        'type',
        'project_id',
        'private_key_id',
        'private_key',
        'client_email',
        'client_id',
        'auth_uri',
        'token_uri'
    ]
    
    issues = []
    for field in required_fields:
        if field not in sa_info:
            issues.append(f"Missing required field: {field}")
    
    if sa_info.get('type') != 'service_account':
        issues.append(f"Invalid type: {sa_info.get('type')} (expected: service_account)")
    
    return issues

def main():
    print("=" * 60)
    print("Google Play Service Account Diagnostic Tool")
    print("=" * 60)
    print()
    
    # Check environment variable
    encoded_json = os.getenv('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON')
    
    if not encoded_json:
        print("❌ GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not found in environment")
        print()
        print("To use this tool:")
        print("1. Get the value from Vercel Dashboard → Environment Variables")
        print("2. Set it temporarily:")
        print("   PowerShell: $env:GOOGLE_PLAY_SERVICE_ACCOUNT_JSON = 'YOUR_BASE64_STRING'")
        print("   Bash: export GOOGLE_PLAY_SERVICE_ACCOUNT_JSON='YOUR_BASE64_STRING'")
        print("3. Run this script again")
        sys.exit(1)
    
    print("✅ Environment variable found")
    print(f"   Length: {len(encoded_json)} characters")
    print()
    
    # Decode
    print("Decoding base64...")
    sa_info = decode_service_account(encoded_json)
    
    if not sa_info:
        print()
        print("Fix:")
        print("1. Verify you copied the complete base64 string from Vercel")
        print("2. Ensure no extra spaces or newlines")
        print("3. Try encoding again from original JSON file:")
        print("   PowerShell: [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content service-account.json -Raw)))")
        sys.exit(1)
    
    print("✅ Successfully decoded")
    print()
    
    # Validate structure
    print("Validating service account structure...")
    issues = validate_service_account(sa_info)
    
    if issues:
        print("❌ Validation failed:")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit(1)
    
    print("✅ Structure is valid")
    print()
    
    # Display key information
    print("=" * 60)
    print("SERVICE ACCOUNT INFORMATION")
    print("=" * 60)
    print(f"Email:      {sa_info.get('client_email')}")
    print(f"Project ID: {sa_info.get('project_id')}")
    print(f"Client ID:  {sa_info.get('client_id')}")
    print(f"Key ID:     {sa_info.get('private_key_id')}")
    print()
    
    # Next steps
    print("=" * 60)
    print("NEXT STEPS - GRANT PERMISSIONS IN GOOGLE PLAY CONSOLE")
    print("=" * 60)
    print()
    print("1. Go to: https://play.google.com/console")
    print("2. Select: SmartBoy app (tuanorg.smartboy)")
    print("3. Navigate: Setup → API access")
    print("4. Find this service account:")
    print(f"   {sa_info.get('client_email')}")
    print()
    print("5. Click the email and grant these permissions:")
    print("   ✅ View app information and download bulk reports (read-only)")
    print("   ✅ View financial data, orders, and cancellation survey responses")
    print("   ✅ Manage orders and subscriptions")
    print()
    print("6. Save and wait 15-30 minutes for propagation")
    print()
    print("7. Redeploy backend:")
    print("   git commit --allow-empty -m 'Refresh Google Play API credentials'")
    print("   git push")
    print()
    print("=" * 60)
    print()
    
    # Check if we can test the API
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        print("Testing API initialization...")
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/androidpublisher']
        )
        
        publisher_api = build('androidpublisher', 'v3', credentials=credentials)
        print("✅ API client initialized successfully")
        print()
        print("⚠️  Note: This doesn't test permissions - only that credentials are valid.")
        print("   You still need to grant permissions in Play Console.")
        print()
    except ImportError:
        print("⚠️  Cannot test API (missing dependencies)")
        print("   Install: pip install google-auth google-api-python-client")
        print()
    except Exception as e:
        print(f"❌ API initialization failed: {e}")
        print()
    
    print("=" * 60)
    print("Diagnostic complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()
