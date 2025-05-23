import json
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, HTTP_REFERER, APP_TITLE
import random
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
client = OpenAI(
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
    default_headers={
        "HTTP-Referer": HTTP_REFERER,
        "X-Title": APP_TITLE
    }
)

def get_analysis(student_data):
    messages = [{
        "role": "user",
        "content": (
                    "Analyze the student's performance based on the provided data. "
                    "Return a JSON object with two keys: 'analysis' and 'questions'. "
                    "'analysis' should contain a summary of the student's weak areas. "
                    "'questions' should be a JSON array of suggested math questions"
                    " and also practice questions that the student can use to improve"
                    ", where each question includes a 'question' field and an 'answer' field. "
                    "Do not include any extra text, explanations, or formatting outside the JSON structure. "
                    f"Student Data: {student_data}"
                )
    }]

    print("Attempts:", messages)
    
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages
    )

    # Extract response
    response_text = completion.choices[0].message.content
    
    try:
        # Parse and return JSON
        # Log the data before calling AI service
        #logger.info("Data before AI analysis:\n" + json.dumps(response_text, indent=4))
        return json.loads(response_text)
    except json.JSONDecodeError:
        print("Error: AI did not return valid JSON.")
        return {"analysis": "No valid response", "questions": []}

def analyze_attempts(attempts):
    """
    Analyze student attempts to identify weak areas and patterns.
    Returns weak areas and specific number ranges where student struggles.
    """
    operation_stats = {
        'Addition': {'correct': 0, 'total': 0, 'numbers': []},
        'AdditionX': {'correct': 0, 'total': 0, 'numbers': []},
        'Subtraction': {'correct': 0, 'total': 0, 'numbers': []},
        'SubtractionX': {'correct': 0, 'total': 0, 'numbers': []},
        'Multiplication': {'correct': 0, 'total': 0, 'numbers': []},
        'Division': {'correct': 0, 'total': 0, 'numbers': []}
    }
    
    # Focus on recent attempts (last 24 hours)
    recent_cutoff = (datetime.now() - timedelta(days=1)).isoformat()
    
    for attempt in attempts:
        if attempt['datetime'] >= recent_cutoff:
            question = attempt['question']
            # Extract numbers from the question
            numbers = [int(n) for n in question.replace('=', ' ').split() if n.isdigit()]
            
            for op_type in operation_stats:
                if op_type in question:
                    operation_stats[op_type]['total'] += 1
                    if attempt['is_correct']:
                        operation_stats[op_type]['correct'] += 1
                    else:
                        operation_stats[op_type]['numbers'].extend(numbers)
                    break
    
    # Identify weak areas and problematic number ranges
    weak_areas = []
    number_ranges = {}
    
    for op_type, stats in operation_stats.items():
        if stats['total'] > 0:
            success_rate = stats['correct'] / stats['total']
            if success_rate < 0.7:  # Less than 70% success rate
                weak_areas.append(op_type)
                # Find number ranges that cause problems
                if stats['numbers']:
                    avg = sum(stats['numbers']) / len(stats['numbers'])
                    number_ranges[op_type] = {
                        'min': min(stats['numbers']),
                        'max': max(stats['numbers']),
                        'avg': round(avg)
                    }
    
    return weak_areas, number_ranges

def generate_practice_questions(attempts, patterns):
    """
    Generate questions using AI, focusing on student's weak areas based on their attempt history.
    """
    # Prepare data for the AI by categorizing attempts
    weak_areas = []
    strong_areas = []
    
    # Filter out attempts with missing data
    valid_attempts = [
        attempt for attempt in attempts 
        if attempt["question"] and (
            (not attempt["is_correct"] and attempt["incorrect_answer"]) or 
            (attempt["is_correct"] and attempt["correct_answer"])
        )
    ]
    
    logger.debug(f"Processing {len(valid_attempts)} valid attempts out of {len(attempts)} total attempts")
    
    for attempt in valid_attempts:
        question_info = {
            "question": attempt["question"].strip(),
            "correct_answer": attempt["correct_answer"].strip() if attempt["correct_answer"] else "",
            "datetime": attempt["datetime"]
        }
        
        if not attempt["is_correct"]:
            question_info["incorrect_answer"] = attempt["incorrect_answer"].strip() if attempt["incorrect_answer"] else ""
            weak_areas.append(question_info)
        else:
            strong_areas.append(question_info)
    
    logger.debug(f"Found {len(weak_areas)} weak areas and {len(strong_areas)} strong areas")

    # If no valid attempts, use fallback questions
    if not valid_attempts:
        logger.debug("No valid attempts found, using fallback questions")
        #return generate_fallback_questions()

    # Create example JSON separately to avoid f-string issues
        response_json_format = '''
        {
        [
            {
            "number": [an incremental integer],
            "topic": [the type of question "algebra"],
            "pattern": [example question pattern "a + _ = b"],
            "question": [example question 500 + _ = 700"],
            "answer": [the answer 200]
            }
        ]
        }
        '''
    # response_json_format = '''
    #     {
    #     "questions": [
    #         {
    #         "number": [an incremental integer],
    #         "topic": [the type of question "algebra"],
    #         "pattern": [example question pattern "a + _ = b"],
    #         "question": [example question 500 + _ = 700"],
    #         "answer": [the answer 200]
    #         }
    #     ]
    #     }
    #     '''


#     example_json = '''
# {
#     "Addition": "23 + 45",
#     "AdditionX": "__ + 45 = 68",
#     "Multiplication1": "7 × 8",
#     "Division1": "56 ÷ 8"
# }'''

    # Process patterns into a more readable format
    pattern_info = []
    for pattern in patterns:
        pattern_info.append(f"{pattern['type']}: {pattern['pattern_text']}")

    difficulty = 'a & b variables must range from -999 to 999. '    

    # Craft a detailed prompt for the AI
    prompt = {
        "role": "user",
        "content": f"""Generate a set of math questions for each question pattern for a student based on their performance history. 

Context:
- Questions they struggled with: {json.dumps(weak_areas, indent=2)}
- Questions they mastered: {json.dumps(strong_areas, indent=2)}
- Available question patterns:
{chr(10).join(pattern_info)}

 Requirements:
1. Generate a question for each question pattern
2. Focus on areas where the student made mistakes
3. Include similar but slightly different versions of questions they got wrong
4. Avoid exact repetition of mastered questions
5. Include at least one question from their strong areas but with increased difficulty
6. {difficulty}

Return ONLY a JSON object for each question pattern, with the following format for each question and answer set: 
{response_json_format}"""
    }

    logger.debug("Sending prompt to OpenAI")
    logger.debug(f"Prompt context - Weak areas: {len(weak_areas)}, Strong areas: {len(strong_areas)}, Patterns: {len(patterns)}")

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[prompt]
        )
        
        # Extract and parse the response
        response_text = completion.choices[0].message.content
        
        # Clean the response text in case it contains any non-JSON text
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        logger.debug(f"Raw AI response: {response_text}")
        
        questions = json.loads(response_text)
        logger.debug(f"Successfully parsed questions: {json.dumps(questions, indent=2)}")
        
        return {
            'questions': questions,
            'timestamp': datetime.now(),
            'message': "Success"
        }
    except json.JSONDecodeError as je:
        logger.error(f"JSON decode error: {str(je)}")
        return generate_fallback_questions(error_message=str(je))
    except Exception as e:
        logger.error(f"Error generating questions with AI: {str(e)}")
        return generate_fallback_questions(error_message=str(e))

def generate_fallback_questions(error_message="Unknown error occurred"):
    """Generate basic questions as a fallback if AI fails"""
    fallback_questions = [
        {
            "number": 1,
            "topic": "addition",
            "pattern": "a + b = _",
            "question": f"{random.randint(10, 99)} + {random.randint(10, 99)} = _",
            "answer": None  # Will be calculated below
        },
        {
            "number": 2,
            "topic": "subtraction",
            "pattern": "_ - b = c",
            "question": f"_ - {random.randint(10, 50)} = {random.randint(10, 50)}",
            "answer": None  # Will be calculated below
        },
        {
            "number": 3,
            "topic": "multiplication",
            "pattern": "a × b = _",
            "question": f"{random.randint(2, 12)} × {random.choice([2, 3, 4, 5, 10])} = _",
            "answer": None  # Will be calculated below
        },
        {
            "number": 4,
            "topic": "division",
            "pattern": "a ÷ b = _",
            "question": f"{random.randint(20, 100)} ÷ {random.choice([2, 5, 10])} = _",
            "answer": None  # Will be calculated below
        }
    ]
    
    # Calculate answers for each question
    for question in fallback_questions:
        if "a + b = _" in question["pattern"]:
            parts = question["question"].split("+")
            a = int(parts[0].strip())
            b = int(parts[1].split("=")[0].strip())
            question["answer"] = a + b
        elif "_ - b = c" in question["pattern"]:
            parts = question["question"].split("-")
            b = int(parts[1].split("=")[0].strip())
            c = int(parts[1].split("=")[1].strip())
            question["answer"] = b + c
        elif "a × b = _" in question["pattern"]:
            parts = question["question"].split("×")
            a = int(parts[0].strip())
            b = int(parts[1].split("=")[0].strip())
            question["answer"] = a * b
        elif "a ÷ b = _" in question["pattern"]:
            parts = question["question"].split("÷")
            a = int(parts[0].strip())
            b = int(parts[1].split("=")[0].strip())
            question["answer"] = a // b
    
    return {
        'questions': fallback_questions,
        'timestamp': datetime.now().isoformat(),
        'message': f"AI question generation failed: {error_message}"
    }

