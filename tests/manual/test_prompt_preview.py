"""
Quick script to test the prompt preview endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test preview endpoint with different students
test_cases = [
    {
        "name": "Grade 1 Student - Simple Math",
        "uid": "test_grade1_uid",
        "question": "What is 2 + 3?",
        "correct_answer": "5",
        "subject_id": 1,
        "subject_name": "Math",
        "has_answered": False
    },
    {
        "name": "Grade 6 Student - Science",
        "uid": "test_grade6_uid",
        "question": "What is photosynthesis?",
        "correct_answer": "The process by which plants make food using sunlight",
        "subject_id": 2,
        "subject_name": "Science",
        "has_answered": False
    },
    {
        "name": "Grade 12 Student - Advanced Math",
        "uid": "test_grade12_uid",
        "question": "Find the derivative of f(x) = 3x² + 2x + 1",
        "correct_answer": "f'(x) = 6x + 2",
        "subject_id": 1,
        "subject_name": "Math",
        "has_answered": False
    }
]

print("=" * 80)
print("TESTING PROMPT PREVIEW ENDPOINT - Grade-Based Tone Configuration")
print("=" * 80)

for test in test_cases:
    print(f"\n{'=' * 80}")
    print(f"TEST CASE: {test['name']}")
    print(f"{'=' * 80}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate-question-help/preview",
            json=test
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Success!")
            print(f"\nGrade Level: {data.get('grade_level', 'None (using default)')}")
            print(f"\nTone Instruction:")
            print(f"  {data['metadata']['tone_instruction']}")
            
            print(f"\n--- FULL PROMPT PREVIEW (first 500 chars) ---")
            prompt = data['prompt']
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            
            # Save full prompt to file
            filename = f"prompt_preview_{test['name'].replace(' ', '_')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Test Case: {test['name']}\n")
                f.write(f"Grade Level: {data.get('grade_level', 'Default')}\n")
                f.write(f"Tone Config:\n")
                f.write(json.dumps(data['tone_config'], indent=2))
                f.write(f"\n\n{'=' * 80}\n")
                f.write(f"FULL PROMPT:\n")
                f.write(f"{'=' * 80}\n\n")
                f.write(prompt)
            
            print(f"\n📄 Full prompt saved to: {filename}")
            
        else:
            print(f"\n❌ Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error - Is the backend server running at {BASE_URL}?")
        print("   Start it with: cd Backend_Python; .\\start-dev.ps1")
        break
    except Exception as e:
        print(f"\n❌ Error: {e}")

print(f"\n{'=' * 80}")
print("TEST COMPLETE")
print(f"{'=' * 80}\n")
