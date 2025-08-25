import json
from openai import OpenAI
from app.config import AI_BRIDGE_BASE_URL, AI_BRIDGE_API_KEY, AI_BRIDGE_MODEL, HTTP_REFERER, APP_TITLE
from app.validators.response_validator import OpenAIResponseValidator
import random
from datetime import datetime, timedelta
import logging

current_response_text = ""
logger = logging.getLogger(__name__)
client = OpenAI(
    base_url=AI_BRIDGE_BASE_URL,
    api_key=AI_BRIDGE_API_KEY,
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
        model=AI_BRIDGE_MODEL,
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

def generate_practice_questions(attempts, patterns, ai_bridge_base_url=None, ai_bridge_api_key=None, ai_bridge_model=None):
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
    
    logger.debug(f"Found {len(weak_areas)} weak areas and {len(strong_areas)} strong areas")    # If no valid attempts, use fallback questions
    if not valid_attempts:
        logger.debug("No valid attempts found, using fallback questions")
        return generate_fallback_questions("No valid attempts found")

    # Create example JSON separately to avoid f-string issues
    response_json_format = '''
    
        [
            {
            "number": [an incremental integer],
            "topic": [the type of question "algebra"],
            "pattern": [example question pattern "a + _ = b"],
            "question": [example question 500 + _ = 700"],
            "answer": [the answer 200]
            }
        ]
    
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
        6. {difficulty}        Return ONLY a JSON object for each question pattern, with the following format for each question and answer set: 
        {response_json_format}        7. Generate JSON output only, exclude any text, narrative or notes. Return JSON data without any wrapping text or formatting. return a cleaned and properly formatted JSON"""
    }
    
    logger.debug("Sending prompt to OpenAI")
    logger.debug(f"Prompt context - Weak areas: {len(weak_areas)}, Strong areas: {len(strong_areas)}, Patterns: {len(patterns)}")    # Start timing the API call
    api_start_time = datetime.now()
    response_time = None
    
    # Initialize global variable to avoid UnboundLocalError
    global current_response_text
    current_response_text = ""
    
    try:
        
        # Use passed configuration or fall back to global config
        api_key = ai_bridge_api_key or AI_BRIDGE_API_KEY
        base_url = ai_bridge_base_url or AI_BRIDGE_BASE_URL
        model = ai_bridge_model or AI_BRIDGE_MODEL
        
        # Create a new client with the specified configuration
        api_client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": HTTP_REFERER,
                "X-Title": APP_TITLE
            }
        )
        
        logger.debug(f"Using AI Bridge config - Model: {model}, Base URL: {base_url}")
        
        completion = api_client.chat.completions.create(
            model=model,
            messages=[prompt]
        )
        
        # Calculate response time
        api_end_time = datetime.now()
        response_time = (api_end_time - api_start_time).total_seconds()        # Extract and parse the response
        response_text = completion.choices[0].message.content
        
        
        #manual mock
        #response_text = '[\n    {\n        "number": 1,\n        "topic": "algebra",\n        "pattern": "a + _ = b",\n        "question": "700 + _ = 900",\n        "answer": "200"\n    },\n    {\n        "number": 2,\n        "topic": "algebra",\n        "pattern": "a - _ = b",\n        "question": "999 - _ = 300",\n        "answer": "699"\n    },\n    {\n        "number": 3,\n        "topic": "algebra",\n        "pattern": "a + b = _",\n        "question": "999 + 999 = _",\n        "answer": "1998"\n    },\n    {\n        "number": 4,\n        "topic": "algebra",\n        "pattern": "a / b = _",\n        "question": "999 / 3 = _",\n        "answer": "333"\n    }\n]'
        #response_text = "```\n[\n  {\n    \"1\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a + _ = b\",\n      \"question\": \"743 + _ = 946\",\n      \"answer\": \"203\"\n    }\n  },\n  {\n    \"2\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a - _ = b\",\n      \"question\": \"1886 - _ = 932\",\n      \"answer\": \"954\"\n    }\n  },\n  {\n    \"3\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a * b = _\",\n      \"question\": \"1593 * _ = 531\",\n      \"answer\": \"3\"\n    }\n  },\n  {\n    \"4\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a + b = _\",\n      \"question\": \"736 + 433 = _\",\n      \"answer\": \"1169\"\n    }\n  },\n  {\n    \"5\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a / b = _\",\n      \"question\": \"890 / _ = 89\",\n      \"answer\": \"10\"\n    }\n  },\n  {\n    \"6\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a * b = _\",\n      \"question\": \"1871 * _ = 18710\",\n      \"answer\": \"10\"\n    }\n  },\n  {\n    \"7\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a / b = _\",\n      \"question\": \"21 / _ = 7\",\n      \"answer\": \"3\"\n    }\n  },\n  {\n    \"8\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a * b = _\",\n      \"question\": \"407 * _ = 1221\",\n      \"answer\": \"3\"\n    }\n  },\n  {\n    \"9\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a * b = _\",\n      \"question\": \"74 * _ = 296\",\n      \"answer\": \"4\"\n    }\n  },\n  {\n    \"10\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a - b = _\",\n      \"question\": \"848 - _ = 717\",\n      \"answer\": \"131\"\n    }\n  },\n  {\n    \"11\": {\n      \"topic\": \"algebra\",\n      \"pattern\": \"a + b = _\",\n      \"question\": \"500 + 300 = _\",\n      \"answer\": \"800\"\n    }\n  }\n]\n```"
        
        current_response_text = response_text
        
        # Validate the AI response using the comprehensive validator
        validator = OpenAIResponseValidator()
        validation_result = validator.validate_partial_response(response_text, min_questions=1)
        
        logger.debug(f"Validation result: {validation_result['is_valid']}")
        if validation_result['errors']:
            logger.warning(f"Validation errors: {validation_result['errors']}")
        if validation_result['warnings']:
            logger.info(f"Validation warnings: {validation_result['warnings']}")
        
        # Log validation summary
        validation_summary = validator.get_validation_summary(validation_result)
        logger.info(f"Response validation summary:\n{validation_summary}")
        
        if validation_result['is_valid']:
            questions = validation_result['questions']
            logger.debug(f"Successfully validated {len(questions)} questions")
            logger.debug(f"AI Bridge API response time: {response_time:.2f} seconds")
            
            return {
                'questions': questions,
                'timestamp': datetime.now(),
                'message': "Success",
                'ai_response': current_response_text,
                'response_time': response_time,
                'validation_result': {
                    'is_valid': validation_result['is_valid'],
                    'is_partial': validation_result.get('is_partial', False),
                    'questions_validated': len(questions),
                    'errors_count': len(validation_result['errors']),
                    'warnings_count': len(validation_result['warnings'])
                }
            }
        else:
            # If validation fails, fall back to fallback questions but include validation info
            logger.error("AI response validation failed, using fallback questions")
            fallback_result = generate_fallback_questions(
                f"Validation failed: {'; '.join(validation_result['errors'][:3])}", 
                current_response_text, 
                response_time
            )
            fallback_result['validation_result'] = {
                'is_valid': False,
                'original_errors': validation_result['errors'],
                'original_warnings': validation_result['warnings']
            }
            return fallback_result
    except json.JSONDecodeError as je:
        # Calculate response time even on error
        if response_time is None:
            api_end_time = datetime.now()
            response_time = (api_end_time - api_start_time).total_seconds()
        
        logger.error(f"JSON decode error: {str(je)}")
        logger.error(f"AI Bridge API response time: {response_time:.2f} seconds")
        return generate_fallback_questions(str(je), current_response_text, response_time)
    except Exception as e:
        # Calculate response time even on error
        if response_time is None:
            api_end_time = datetime.now()
            response_time = (api_end_time - api_start_time).total_seconds()
        
        logger.error(f"Error generating questions with AI: {str(e)}")
        api_key = ai_bridge_api_key or AI_BRIDGE_API_KEY
        base_url = ai_bridge_base_url or AI_BRIDGE_BASE_URL
        model = ai_bridge_model or AI_BRIDGE_MODEL
        logger.error(f"ai client info : {model} {api_key} {base_url}")
        logger.error(f"AI Bridge API response time: {response_time:.2f} seconds")
        return generate_fallback_questions(str(e), current_response_text, response_time)

def generate_fallback_questions(error_message="Unknown error occurred", current_response_text="", response_time=None):
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
    
    # Only show last 4 digits of API key for security
    api_key_last3 = AI_BRIDGE_API_KEY[-3:] if AI_BRIDGE_API_KEY else "None"
    return {
        'questions': fallback_questions,
        'timestamp': datetime.now(),
        'message': f"AI question generation failed: {error_message} {AI_BRIDGE_MODEL} {api_key_last3} {AI_BRIDGE_BASE_URL}",
        'ai_response': current_response_text,
        'response_time': response_time
    }

