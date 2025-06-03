#!/usr/bin/env python3

import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_with_custom_openai_config():
    """Test with custom OpenAI parameters"""
    request_data = {
        'uid': 'test-firebase-uid-api-1',
        'openai_base_url': 'https://api.openai.com/v1',
        'openai_api_key': 'test-key',
        'openai_model': 'gpt-4'
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

def test_with_none_openai_config():
    """Test with None OpenAI parameters (uses defaults)"""
    request_data = {
        'uid': 'test-firebase-uid-api-2',
        'openai_base_url': None,
        'openai_api_key': None,
        'openai_model': None
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
    print("Testing generate-questions endpoint with custom OpenAI config:")
    test_with_custom_openai_config()
    
    print("\nTesting generate-questions endpoint with default OpenAI config:")
    test_with_none_openai_config()
