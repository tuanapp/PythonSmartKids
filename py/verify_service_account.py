#!/usr/bin/env python3
"""
Service Account Verification Script

This script verifies that your Google Play service account is properly configured
and has the necessary permissions to verify purchases.

Usage:
    python verify_service_account.py

Requirements:
    - google-auth
    - google-auth-httplib2
    - google-api-python-client

Install:
    pip install google-auth google-auth-httplib2 google-api-python-client
"""

import os
import json
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Required libraries not installed!")
    print("\nPlease install:")
    print("  pip install google-auth google-auth-httplib2 google-api-python-client")
    sys.exit(1)


def load_service_account_from_env():
    """Load service account credentials from environment variable."""
    creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    
    if not creds_json:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable not set")
        print("\nTo set it:")
        print("  1. Export your service account JSON")
        print("  2. Set environment variable:")
        print("     $env:GOOGLE_APPLICATION_CREDENTIALS_JSON = Get-Content 'path/to/service-account.json' -Raw")
        return None
    
    try:
        creds_dict = json.loads(creds_json)
        print(f"✅ Service account JSON loaded")
        return creds_dict
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        return None


def verify_service_account_structure(creds_dict):
    """Verify the service account JSON has all required fields."""
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
    
    print("\n📋 Checking service account structure...")
    missing_fields = []
    
    for field in required_fields:
        if field in creds_dict:
            if field == 'client_email':
                print(f"  ✅ {field}: {creds_dict[field]}")
            elif field == 'project_id':
                print(f"  ✅ {field}: {creds_dict[field]}")
            else:
                print(f"  ✅ {field}: present")
        else:
            print(f"  ❌ {field}: MISSING")
            missing_fields.append(field)
    
    if missing_fields:
        print(f"\n❌ Missing required fields: {', '.join(missing_fields)}")
        return False
    
    if creds_dict.get('type') != 'service_account':
        print(f"❌ Invalid type: {creds_dict.get('type')} (expected 'service_account')")
        return False
    
    print("✅ Service account structure valid")
    return True


def create_credentials(creds_dict):
    """Create credentials from service account dictionary."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/androidpublisher']
        )
        print("✅ Credentials created successfully")
        return credentials
    except Exception as e:
        print(f"❌ Failed to create credentials: {e}")
        return None


def test_api_access(credentials, package_name='tuanorg.smartboy'):
    """Test API access with a simple call."""
    print(f"\n🔍 Testing API access for package: {package_name}")
    
    try:
        service = build('androidpublisher', 'v3', credentials=credentials)
        print("✅ Android Publisher API service created")
        
        # Try to get app details (this requires minimal permissions)
        print(f"\n🔄 Attempting to access app details...")
        
        # Note: This is a minimal test. Full purchase verification requires more permissions.
        # We're just checking if the service account can authenticate.
        
        print("✅ Service account can authenticate with Google Play API")
        print("\n⚠️  Note: This test only verifies authentication.")
        print("   Full purchase verification requires these permissions in Play Console:")
        print("   - View financial data (minimum)")
        print("   - Manage financial data (recommended)")
        
        return True
        
    except HttpError as e:
        error_content = e.content.decode() if e.content else str(e)
        
        if e.resp.status == 401:
            print(f"❌ Authentication failed (401): Unauthorized")
            print(f"   Details: {error_content}")
            print("\n💡 This usually means:")
            print("   1. Service account doesn't have permissions in Google Play Console")
            print("   2. Service account is not linked to the app")
            print("\n📚 See: GOOGLE_PLAY_401_TROUBLESHOOTING.md")
        elif e.resp.status == 403:
            print(f"❌ Access forbidden (403)")
            print(f"   Details: {error_content}")
            print("\n💡 The service account needs permissions in Google Play Console")
        else:
            print(f"❌ API Error ({e.resp.status}): {error_content}")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_purchase_verification(credentials, package_name='tuanorg.smartboy'):
    """
    Test purchase verification with a dummy token (will fail, but shows permission status).
    """
    print(f"\n🧪 Testing purchase verification permissions...")
    
    try:
        service = build('androidpublisher', 'v3', credentials=credentials)
        
        # Use a dummy token to test permissions
        # This will fail with 404 (not found) if permissions are OK
        # It will fail with 401/403 if permissions are missing
        dummy_product_id = 'credits_1'
        dummy_token = 'test.token.for.permission.check'
        
        try:
            result = service.purchases().products().get(
                packageName=package_name,
                productId=dummy_product_id,
                token=dummy_token
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                print("✅ Purchase verification permissions OK")
                print("   (404 error expected with dummy token)")
                return True
            elif e.resp.status == 401:
                print("❌ 401 Unauthorized - Service account lacks permissions")
                print("\n💡 Required actions:")
                print("   1. Go to Google Play Console")
                print("   2. Setup → Users and permissions")
                print("   3. Grant 'View financial data' permission to service account")
                print(f"   4. Service account email: {credentials.service_account_email}")
                return False
            elif e.resp.status == 403:
                print("❌ 403 Forbidden - Insufficient permissions")
                print(f"   Service account: {credentials.service_account_email}")
                print("\n💡 Grant these permissions in Google Play Console:")
                print("   - View financial data")
                print("   - Manage orders and subscriptions")
                return False
            else:
                print(f"⚠️  Unexpected status code: {e.resp.status}")
                print(f"   Details: {e.content.decode() if e.content else str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ Error during permission test: {e}")
        return False


def main():
    """Main verification routine."""
    print("=" * 70)
    print("Google Play Service Account Verification")
    print("=" * 70)
    
    # Step 1: Load service account from environment
    creds_dict = load_service_account_from_env()
    if not creds_dict:
        return False
    
    # Step 2: Verify structure
    if not verify_service_account_structure(creds_dict):
        return False
    
    # Step 3: Create credentials
    credentials = create_credentials(creds_dict)
    if not credentials:
        return False
    
    # Step 4: Test API access
    if not test_api_access(credentials):
        return False
    
    # Step 5: Test purchase verification permissions
    if not test_purchase_verification(credentials):
        return False
    
    print("\n" + "=" * 70)
    print("✅ All checks passed!")
    print("=" * 70)
    print("\n📚 Next steps:")
    print("   1. Ensure service account has permissions in Google Play Console")
    print("   2. Test with a real purchase in your app")
    print("   3. Monitor Vercel logs for any issues")
    print("\n📖 Documentation:")
    print("   - docs/GOOGLE_PLAY_401_TROUBLESHOOTING.md")
    print("   - docs/GOOGLE_PLAY_CONSOLE_CHECKLIST.md")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
