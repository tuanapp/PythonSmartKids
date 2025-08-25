#!/usr/bin/env python3
import requests
import json

def test_exact_client_format():
    print("Testing with exact client format...")
    
    # This is the exact payload from the client HTML
    payload = {
        "uid": "user-123456",
        "ai_bridge_base_url": "https://api.forge.tensorblock.co/v1/chat/completions",
        "ai_bridge_api_key": "forge-MGRk0dd31aa7edf58b0ca5b6cfffc7a70092",
        "ai_bridge_model": "Gemini/models/gemini-2.0-flash"
    }
    
    url = "http://localhost:8000/generate-questions"
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS!")
            print(f"Questions: {len(data.get('questions', []))}")
            print(f"Time: {data.get('response_time_seconds')} sec")
            print(f"Validation: {data.get('validation_status')}")
        else:
            print("❌ FAILED")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_exact_client_format()
