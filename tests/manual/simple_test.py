#!/usr/bin/env python3
"""
Simple test script to verify the generate-questions endpoint
"""
import requests
import json

def simple_test():
    print("Starting API test...")
    
    try:
        url = "http://localhost:8000/generate-questions"
        payload = {"uid": "test_user_123"}
        
        print(f"Making request to: {url}")
        print(f"Payload: {payload}")
        
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS!")
            print(f"Questions generated: {len(data.get('questions', []))}")
            print(f"Response time: {data.get('response_time_seconds')} seconds")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simple_test()
