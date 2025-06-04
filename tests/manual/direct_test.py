#!/usr/bin/env python3
import sys
import os

# Add the project root to Python path
sys.path.append('c:/Private/GIT/PythonSmartKids')

import requests
import json

def direct_test():
    print("Starting direct API test...")
    
    url = "http://localhost:8000/generate-questions"
    payload = {"uid": "test_user_123"}
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Questions: {len(data.get('questions', []))}")
            print(f"Time: {data.get('response_time_seconds')} sec")
        else:
            print("❌ FAILED")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    direct_test()
