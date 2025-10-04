"""
Manual API Test for User Registration

This script tests the running development server by calling the registration API directly.
Make sure the server is running on localhost:8000 before running this test.
"""

import requests
import json
from datetime import datetime, timezone

# Server configuration
SERVER_URL = "http://localhost:8000"
REGISTER_ENDPOINT = f"{SERVER_URL}/users/register"

def test_registration_api():
    """Test the registration API with a real HTTP request."""
    
    print("🚀 Testing User Registration API")
    print(f"Server: {SERVER_URL}")
    print("=" * 50)
    
    # Test user data with realistic Firebase UID format
    test_user = {
        "uid": "ManualTestUid123456789012",  # 28 character Firebase UID format
        "email": "manual.test@example.com",
        "name": "Manual Test User",
        "displayName": "Manual Test",
        "gradeLevel": 5,
        "registrationDate": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        print(f"📤 Sending registration request...")
        print(f"Data: {json.dumps(test_user, indent=2)}")
        
        # Send registration request
        response = requests.post(
            REGISTER_ENDPOINT,
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n📥 Response received:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Registration successful!")
            print(f"Response: {json.dumps(response_data, indent=2)}")
            
            # Verify response contains expected fields
            expected_fields = ["message", "uid", "email", "name", "registrationDate"]
            for field in expected_fields:
                if field in response_data:
                    print(f"✅ {field}: {response_data[field]}")
                else:
                    print(f"❌ Missing field: {field}")
            
            return True
            
        else:
            print(f"❌ Registration failed!")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure the server is running on localhost:8000")
        print("💡 Start the server with: .\\start-dev.ps1")
        return False
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out!")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_health_check():
    """Test if the server is responding."""
    try:
        print(f"\n🔍 Checking server health...")
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Server is healthy")
            return True
        else:
            print(f"⚠️ Server responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Server not reachable")
        return False
        
    except Exception as e:
        print(f"⚠️ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Manual API Test Starting...")
    print()
    
    # Check server health first
    if test_health_check():
        # Run registration test
        success = test_registration_api()
        
        if success:
            print(f"\n🎉 All tests passed! Registration API is working correctly.")
        else:
            print(f"\n❌ Tests failed! Check server logs for details.")
    else:
        print(f"\n💡 Start the development server first:")
        print(f"   cd Backend_Python")
        print(f"   .\\start-dev.ps1")
    
    print(f"\n📊 Test completed.")