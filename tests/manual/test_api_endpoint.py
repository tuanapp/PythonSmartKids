#!/usr/bin/env python3
"""
Test script to verify the generate-questions endpoint works with the new request format
"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_generate_questions_endpoint():
    """Test the generate-questions endpoint with various configurations"""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/generate-questions"
    
    print("🧪 Testing PythonSmartKids API - Generate Questions Endpoint")
    print("=" * 60)
    
    # Test 1: Basic request with just UID
    print("\n1. Testing basic request with UID only...")
    
    payload_basic = {
        "uid": "test_user_123"
    }
    
    try:
        response = requests.post(endpoint, json=payload_basic, timeout=30)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success! Generated {len(data.get('questions', []))} questions")
            print(f"   Response Time: {data.get('response_time_seconds', 'N/A')} seconds")
            print(f"   Validation Status: {data.get('validation_status', 'N/A')}")
            print(f"   First Question: {data.get('questions', [{}])[0].get('question', 'N/A')[:50]}...")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 2: Request with custom OpenAI configuration
    print("\n2. Testing request with custom OpenAI configuration...")
    
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        payload_custom = {
            "uid": "test_user_456",
            "openai_api_key": openai_api_key,
            "openai_model": "gpt-3.5-turbo",
            "openai_base_url": "https://api.openai.com/v1"
        }
        
        try:
            response = requests.post(endpoint, json=payload_custom, timeout=30)
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success! Generated {len(data.get('questions', []))} questions")
                print(f"   Response Time: {data.get('response_time_seconds', 'N/A')} seconds")
                print(f"   Validation Status: {data.get('validation_status', 'N/A')}")
                print(f"   Model Used: Custom OpenAI")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
    else:
        print("   ⚠️  Skipped - No OPENAI_API_KEY found in environment")
    
    # Test 3: Invalid request (missing UID)
    print("\n3. Testing invalid request (missing UID)...")
    
    payload_invalid = {}
    
    try:
        response = requests.post(endpoint, json=payload_invalid, timeout=30)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 422:
            print("   ✅ Correctly rejected invalid request")
        else:
            print(f"   ⚠️  Unexpected response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 4: Check API documentation
    print("\n4. Testing API documentation availability...")
    
    try:
        docs_response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"   Docs Status Code: {docs_response.status_code}")
        
        if docs_response.status_code == 200:
            print("   ✅ API documentation is accessible")
        else:
            print("   ❌ API documentation not accessible")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Docs request failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 API endpoint testing completed!")

if __name__ == "__main__":
    test_generate_questions_endpoint()
