#!/usr/bin/env python3

import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_with_custom_ai_bridge_config():
    """Test with custom AI Bridge parameters"""
    request_data = {
        'uid': 'test-firebase-uid-api-1',
        'ai_bridge_base_url': 'https://api.forge.tensorblock.co/v1/chat/completions',
        'ai_bridge_api_key': 'forge-test-key',
        'ai_bridge_model': 'Gemini/models/gemini-2.0-flash'
    }
    response = client.post('/generate-questions', json=request_data)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        response_json = response.json()
        print(f'Questions count: {len(response_json.get("questions", []))}')
        print(f'Response time: {response_json.get("response_time", "N/A")} seconds')
        print(f'Message: {response_json.get("message", "N/A")}')
        print(f'Has timestamp: {"timestamp" in response_json}')
    else:
        print(f'Error response: {response.text}')

def test_with_none_ai_bridge_config():
    """Test with None AI Bridge parameters (uses defaults)"""
    request_data = {
        'uid': 'test-firebase-uid-api-2',
        'ai_bridge_base_url': None,
        'ai_bridge_api_key': None,
        'ai_bridge_model': None
    }
    response = client.post('/generate-questions', json=request_data)
    print(f'\nStatus: {response.status_code}')
    if response.status_code == 200:
        response_json = response.json()
        print(f'Questions count: {len(response_json.get("questions", []))}')
        print(f'Response time: {response_json.get("response_time", "N/A")} seconds')
        print(f'Message: {response_json.get("message", "N/A")}')
        print(f'Has timestamp: {"timestamp" in response_json}')
    else:
        print(f'Error response: {response.text}')

if __name__ == "__main__":
    print("Testing generate-questions endpoint with custom AI Bridge config:")
    test_with_custom_ai_bridge_config()
    
    print("\nTesting generate-questions endpoint with default AI Bridge config:")
    test_with_none_ai_bridge_config()
