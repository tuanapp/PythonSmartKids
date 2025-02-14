from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
)

def get_analysis(student_data):
    messages = [{
        "role": "user",
        "content": f"Analyze this student's performance and suggest questions: {student_data}"
    }]

    completion = client.chat.completions.create(
        model="qwen/qwen2.5-vl-72b-instruct:free",
        messages=messages
    )
    
    return completion.choices[0].message.content
