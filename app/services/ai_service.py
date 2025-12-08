import json
from openai import OpenAI
from app.config import AI_BRIDGE_BASE_URL, AI_BRIDGE_API_KEY, AI_BRIDGE_MODEL, AI_FALLBACK_MODEL_1, HTTP_REFERER, APP_TITLE, MAX_ATTEMPTS_HISTORY_LIMIT
from app.validators.response_validator import OpenAIResponseValidator
from app.services.prompt_service import PromptService
import random
from datetime import datetime, timedelta
import logging
import time

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

def generate_practice_questions(uid, attempts, patterns, ai_bridge_base_url=None, ai_bridge_api_key=None, ai_bridge_model=None, level=None, is_live=1):
    """
    Generate questions using AI, focusing on student's weak areas based on their attempt history.
    
    Args:
        uid: Firebase User UID for tracking LLM interactions
        attempts: List of student attempts
        patterns: List of question patterns
        ai_bridge_base_url: Optional custom AI bridge URL
        ai_bridge_api_key: Optional custom AI API key
        ai_bridge_model: Optional custom AI model name
        level: Optional difficulty level
        is_live: 1=live production call, 0=test/local call (default: 1)
        
    Returns:
        Dictionary with questions and metadata, including prompt_id for tracking
    """
    # Initialize Prompt service
    prompt_service = PromptService()
    prompt_id = None
    
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
    
    # Determine if this is a new user (no attempts at all) or a user with invalid attempt data
    is_new_user = len(attempts) == 0
    has_invalid_data_only = len(attempts) > 0 and not valid_attempts
    
    # If user has attempts but they're all invalid, use fallback questions
    if has_invalid_data_only:
        logger.warning("User has attempts but none are valid (missing required fields), using fallback questions")
        return generate_fallback_questions("Invalid attempt data", attempts=attempts, level=level, prompt_text="")
    
    # For new users with no attempts, continue to generate AI questions from patterns
    if is_new_user:
        logger.info("New user detected (zero attempts), generating questions from patterns without history")

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
        pattern_entry = f"{pattern['type']}: {pattern['pattern_text']}"
        # if pattern.get('level'):
        #     pattern_entry += f" [Level {pattern['level']}]"
        if pattern.get('notes'):
            pattern_entry += f" (Notes: {pattern['notes']})"
        pattern_info.append(pattern_entry)

    difficulty = 'a & b variables must range from -999 to 999. '    

    # Craft a detailed prompt for the AI based on whether this is a new user or existing user
    if is_new_user:
        # Prompt for new users without attempt history
        prompt = {
            "role": "user",
            "content": f"""Generate a set of math questions for a NEW student who is just starting. 

            Context:
            - This is a new student with no previous attempt history
            - Available question patterns:
            {chr(10).join(pattern_info)}

            Requirements:
            1. Generate a question for each question pattern
            2. Start with appropriate difficulty for a beginner
            3. Cover a variety of question types to assess the student's initial skill level
            4. Follow any special formatting requirements mentioned in the pattern notes (e.g., decimal places, units, etc.)
            5. Consider the difficulty level indicated in square brackets [Level X] when generating questions
            6. {difficulty}
            
            Return ONLY a JSON object for each question pattern, with the following format for each question and answer set: 
            {response_json_format}
            
            7. Generate JSON output only, exclude any text, narrative or notes. Return JSON data without any wrapping text or formatting. return a cleaned and properly formatted JSON"""
        }
    else:
        # Prompt for existing users with attempt history
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
            6. Follow any special formatting requirements mentioned in the pattern notes (e.g., decimal places, units, etc.)
            7. Consider the difficulty level indicated in square brackets [Level X] when generating questions
            8. {difficulty}
            
            Return ONLY a JSON object for each question pattern, with the following format for each question and answer set: 
            {response_json_format}
            
            9. Generate JSON output only, exclude any text, narrative or notes. Return JSON data without any wrapping text or formatting. return a cleaned and properly formatted JSON"""
        }
    
    logger.debug("Sending prompt to OpenAI")
    if is_new_user:
        logger.info(f"Generating questions for NEW USER - Patterns: {len(patterns)}")
    else:
        logger.debug(f"Prompt context - Weak areas: {len(weak_areas)}, Strong areas: {len(strong_areas)}, Patterns: {len(patterns)}")    
    
    # Start timing the API call
    api_start_time_ms = int(time.time() * 1000)  # Milliseconds
    response_time_ms = None
    
    # Initialize global variable to avoid UnboundLocalError
    global current_response_text
    current_response_text = ""
    
    # Variables for LLM logging
    model_name = None
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    status = 'success'
    error_message = None
    prompt_text = ""
    
    # Determine which models to try (primary + fallback)
    api_key = ai_bridge_api_key or AI_BRIDGE_API_KEY
    base_url = ai_bridge_base_url or AI_BRIDGE_BASE_URL
    primary_model = ai_bridge_model or AI_BRIDGE_MODEL
    fallback_model = AI_FALLBACK_MODEL_1
    
    # List of models to try in order
    models_to_try = [primary_model]
    # Only add fallback if it's different from primary and not empty
    if fallback_model and fallback_model != primary_model:
        models_to_try.append(fallback_model)
    
    last_error = None
    last_error_model = None
    
    for attempt_index, model in enumerate(models_to_try):
        is_fallback_attempt = attempt_index > 0
        model_name = model  # Save for logging
        
        if is_fallback_attempt:
            logger.info(f"Primary model failed, trying fallback model: {model}")
            # Reset timing for fallback attempt
            api_start_time_ms = int(time.time() * 1000)
            response_time_ms = None
            current_response_text = ""
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
        
        try:
            # Create a new client with the specified configuration
            api_client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": HTTP_REFERER,
                    "X-Title": APP_TITLE
                }
            )
            
            logger.debug(f"Using AI Bridge config - Model: {model}, Base URL: {base_url}, Attempt: {attempt_index + 1}/{len(models_to_try)}")
            
            # Save prompt text for logging
            prompt_text = prompt['content']
            
            completion = api_client.chat.completions.create(
                model=model,
                messages=[prompt]
            )
            
            # Calculate response time in milliseconds
            api_end_time_ms = int(time.time() * 1000)
            response_time_ms = api_end_time_ms - api_start_time_ms
            
            # Extract and parse the response
            response_text = completion.choices[0].message.content
            
            # Extract token usage from completion (if available)
            if hasattr(completion, 'usage') and completion.usage:
                prompt_tokens = completion.usage.prompt_tokens
                completion_tokens = completion.usage.completion_tokens
                total_tokens = completion.usage.total_tokens
                logger.debug(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
            
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
                logger.debug(f"AI Bridge API response time: {response_time_ms}ms")
                
                # Log prompt interaction (success case)
                prompt_id = prompt_service.record_prompt(
                    uid=uid,
                    request_type='question_generation',
                    request_text=prompt_text,
                    response_text=current_response_text,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    response_time_ms=response_time_ms,
                    status='success',
                    error_message=None,
                    is_live=is_live,  # Use passed is_live parameter
                    level=level,
                    source='api' if not is_fallback_attempt else 'fallback_api'
                )
                
                return {
                    'questions': questions,
                    'timestamp': datetime.now(),
                    'message': "Success" if not is_fallback_attempt else f"Success (fallback: {model})",
                    'ai_response': current_response_text,
                    'ai_request': prompt['content'],  # Include the prompt text
                    'response_time': response_time_ms / 1000.0,  # Convert to seconds for backward compatibility
                    'prompt_id': prompt_id,  # Add prompt ID
                    'validation_result': {
                        'is_valid': validation_result['is_valid'],
                        'is_partial': validation_result.get('is_partial', False),
                        'questions_validated': len(questions),
                        'errors_count': len(validation_result['errors']),
                        'warnings_count': len(validation_result['warnings']),
                        'ai_model': model,
                        'used_fallback': is_fallback_attempt,
                        'historical_records': f"{len(attempts)} db attempts used out of {MAX_ATTEMPTS_HISTORY_LIMIT} max",
                        'level': level,
                        'is_new_user': is_new_user,
                        'user_type': 'new_user' if is_new_user else 'returning_user'
                    }
                }
            else:
                # Validation failed - if we have more models to try, continue
                last_error = f"Validation failed: {'; '.join(validation_result['errors'][:3])}"
                last_error_model = model
                
                if is_fallback_attempt or len(models_to_try) == 1:
                    # This was the last model, fall back to hardcoded questions
                    status = 'error'
                    error_message = last_error
                    
                    # Log prompt interaction (validation failure)
                    prompt_id = prompt_service.record_prompt(
                        uid=uid,
                        request_type='question_generation',
                        request_text=prompt_text,
                        response_text=current_response_text,
                        model_name=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        response_time_ms=response_time_ms,
                        status=status,
                        error_message=error_message,
                        is_live=is_live,
                        level=level,
                        source='api'
                    )
                    
                    logger.error("AI response validation failed, using fallback questions")
                    fallback_result = generate_fallback_questions(
                        error_message, 
                        current_response_text, 
                        response_time_ms / 1000.0,  # Convert to seconds
                        attempts,
                        level,
                        prompt['content']  # Pass the prompt text
                    )
                    fallback_result['validation_result'] = {
                        'is_valid': False,
                        'original_errors': validation_result['errors'],
                        'original_warnings': validation_result['warnings'],
                        'historical_records': f"{len(attempts)} db attempts used out of {MAX_ATTEMPTS_HISTORY_LIMIT} max",
                        'level': level,
                        'is_new_user': is_new_user,
                        'user_type': 'new_user' if is_new_user else 'returning_user'
                    }
                    fallback_result['prompt_id'] = prompt_id  # Add prompt ID
                    return fallback_result
                else:
                    # More models available, log and continue
                    logger.warning(f"Model {model} validation failed, will try fallback model")
                    continue
                    
        except json.JSONDecodeError as je:
            last_error = f"JSON decode error: {str(je)}"
            last_error_model = model
            
            if is_fallback_attempt or len(models_to_try) == 1:
                # Calculate response time even on error
                if response_time_ms is None:
                    api_end_time_ms = int(time.time() * 1000)
                    response_time_ms = api_end_time_ms - api_start_time_ms
                
                status = 'error'
                error_message = last_error
                
                # Log prompt interaction (JSON error)
                prompt_id = prompt_service.record_prompt(
                    uid=uid,
                    request_type='question_generation',
                    request_text=prompt_text,
                    response_text=current_response_text,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    response_time_ms=response_time_ms,
                    status=status,
                    error_message=error_message,
                    is_live=is_live,
                    level=level,
                    source='fallback'
                )
                
                logger.error(f"JSON decode error: {str(je)}")
                logger.error(f"AI Bridge API response time: {response_time_ms}ms")
                
                fallback_result = generate_fallback_questions(
                    str(je), current_response_text, response_time_ms / 1000.0, attempts, level, prompt_text
                )
                fallback_result['prompt_id'] = prompt_id
                return fallback_result
            else:
                # More models available, log and continue
                logger.warning(f"Model {model} JSON decode error, will try fallback model: {str(je)}")
                continue
            
        except Exception as e:
            last_error = f"Exception: {str(e)}"
            last_error_model = model
            
            if is_fallback_attempt or len(models_to_try) == 1:
                # Calculate response time even on error
                if response_time_ms is None:
                    api_end_time_ms = int(time.time() * 1000)
                    response_time_ms = api_end_time_ms - api_start_time_ms
                
                status = 'error'
                error_message = last_error
                
                # Log prompt interaction (general error)
                prompt_id = prompt_service.record_prompt(
                    uid=uid,
                    request_type='question_generation',
                    request_text=prompt_text if prompt_text else "Error before prompt creation",
                    response_text=current_response_text,
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    response_time_ms=response_time_ms,
                    status=status,
                    error_message=error_message,
                    is_live=is_live,
                    level=level,
                    source='fallback'
                )
                
                logger.error(f"Error generating questions with AI: {str(e)}")
                logger.error(f"ai client info : {model} {api_key} {base_url}")
                logger.error(f"AI Bridge API response time: {response_time_ms}ms")
                
                fallback_result = generate_fallback_questions(
                    str(e), current_response_text, response_time_ms / 1000.0, attempts, level, prompt_text if prompt_text else ""
                )
                fallback_result['prompt_id'] = prompt_id
                return fallback_result
            else:
                # More models available, log and continue
                logger.warning(f"Model {model} exception, will try fallback model: {str(e)}")
                continue
    
    # This should not be reached, but just in case all models fail without returning
    logger.error(f"All AI models failed. Last error from {last_error_model}: {last_error}")
    return generate_fallback_questions(
        last_error or "All AI models failed", 
        current_response_text, 
        None, 
        attempts, 
        level, 
        prompt_text if prompt_text else ""
    )

def generate_fallback_questions(error_message="Unknown error occurred", current_response_text="", response_time=None, attempts=None, level=None, prompt_text=""):
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
    
    # If current_response_text is empty (no AI response), use fallback questions as response
    if not current_response_text:
        current_response_text = json.dumps(fallback_questions, indent=2)
    
    # Build the return response
    result = {
        'questions': fallback_questions,
        'timestamp': datetime.now(),
        'message': f"AI question generation failed: {error_message} {AI_BRIDGE_MODEL} {api_key_last3} {AI_BRIDGE_BASE_URL}",
        'ai_response': current_response_text,
        'ai_request': prompt_text if prompt_text else f"Fallback questions generated due to error: {error_message}",  # Include ai_request for prompt storage
        'response_time': response_time
    }
    
    # Add historical records info if attempts data is available
    if attempts is not None:
        is_new_user_fallback = len(attempts) == 0
        result['validation_result'] = {
            'is_valid': False,
            'historical_records': f"{len(attempts)} db attempts used out of {MAX_ATTEMPTS_HISTORY_LIMIT} max",
            'level': level,
            'is_new_user': is_new_user_fallback,
            'user_type': 'new_user' if is_new_user_fallback else 'returning_user'
        }
    
    return result

#test