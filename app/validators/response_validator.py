import json
import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class OpenAIResponseValidator:
    """
    Comprehensive validator for OpenAI response format.
    Validates that AI responses adhere to the required structure for math questions.
    """
    
    def __init__(self):
        self.required_fields = ['number', 'topic', 'pattern', 'question', 'answer']
        self.valid_topics = [
            'addition', 'subtraction', 'multiplication', 'division',
            'algebra', 'geometry', 'fractions', 'decimals', 'percentages'
        ]
    
    def validate_response(self, response_text: str) -> Dict[str, Any]:
        """
        Validate a complete AI response.
        
        Args:
            response_text: Raw response text from AI
            
        Returns:
            Dict containing validation results
        """
        result = {
            'is_valid': False,
            'questions': [],
            'errors': [],
            'warnings': [],
            'metadata': {
                'original_text': response_text,
                'cleaned_text': None,
                'total_questions': 0,
                'valid_questions': 0,
                'validation_time': datetime.now().isoformat()
            }
        }
        
        try:
            # Handle empty or null responses
            if not response_text or not response_text.strip():
                result['errors'].append("Empty or null response")
                return result
            
            # Clean and parse JSON
            cleaned_text, parsed_data = self._parse_json_response(response_text)
            result['metadata']['cleaned_text'] = cleaned_text
            
            if parsed_data is None:
                result['errors'].append("JSON parsing failed")
                return result
              # Validate structure
            questions = self._validate_structure(parsed_data)
            if not questions:
                if isinstance(parsed_data, dict) and not any(key in parsed_data for key in ['questions']):
                    result['errors'].append("Expected list or response contains no questions")
                else:
                    result['errors'].append("Response contains no questions")
                return result
            
            result['metadata']['total_questions'] = len(questions)
            
            # Check for empty list
            if len(questions) == 0:
                result['errors'].append("Response contains no questions")
                return result
            
            # Check for too many questions
            if len(questions) > 50:
                result['warnings'].append(f"Response contains {len(questions)} questions, which is unusually high")
            
            # Validate each question
            valid_questions = []
            for i, question in enumerate(questions):
                validation = self._validate_question(question, i + 1)
                if validation['is_valid']:
                    valid_questions.append(validation['question'])
                else:
                    result['errors'].extend(validation['errors'])
                result['warnings'].extend(validation['warnings'])
            
            result['questions'] = valid_questions
            result['metadata']['valid_questions'] = len(valid_questions)
            result['is_valid'] = len(valid_questions) > 0
            
            return result
            
        except Exception as e:
            result['errors'].append(f"Validation exception: {str(e)}")
            logger.error(f"Validation error: {e}", exc_info=True)
            return result
    
    def validate_partial_response(self, response_text: str, min_questions: int = 1) -> Dict[str, Any]:
        """
        Validate response allowing partial success.
        
        Args:
            response_text: Raw response text from AI
            min_questions: Minimum number of valid questions required
            
        Returns:
            Dict containing validation results
        """
        result = self.validate_response(response_text)
        
        # For partial validation, we're more lenient
        if len(result['questions']) >= min_questions:
            result['is_valid'] = True
            result['is_partial'] = len(result['questions']) < result['metadata']['total_questions']
        else:
            result['is_valid'] = False
            result['is_partial'] = False
        
        return result
    
    def _parse_json_response(self, response_text: str) -> Tuple[str, Optional[Union[List, Dict]]]:
        """
        Clean and parse JSON from AI response text.
        Handles various formats including markdown code blocks.
        """
        if not response_text or not response_text.strip():
            return "", None
        
        # Store original for logging
        original = response_text.strip()
        
        # Remove markdown code blocks if present
        cleaned = self._clean_response_text(original)
        
        # Try to fix common JSON formatting issues
        cleaned = self._fix_json_formatting(cleaned)
        
        try:
            # Try to parse as JSON
            parsed = json.loads(cleaned)
            return cleaned, parsed
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            
            # Try to extract JSON from text
            json_match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if json_match:
                try:
                    fixed_json = self._fix_json_formatting(json_match.group())
                    parsed = json.loads(fixed_json)
                    return fixed_json, parsed
                except json.JSONDecodeError:
                    pass
            
            # Try to find object-style JSON
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    fixed_json = self._fix_json_formatting(json_match.group())
                    parsed = json.loads(fixed_json)
                    return fixed_json, parsed
                except json.JSONDecodeError:
                    pass
        
        return cleaned, None
    
    def _clean_response_text(self, text: str) -> str:
        """
        Clean response text by removing markdown formatting and extra whitespace.
        """
        # Remove markdown code blocks
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Remove common prefixes/suffixes
        text = re.sub(r'^(?:Here\'s|Here is|The|Response:).*?(?:\n|$)', '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _fix_json_formatting(self, text: str) -> str:
        """
        Fix common JSON formatting issues like trailing commas.
        """
        # Remove trailing commas before closing braces and brackets
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*\]', ']', text)
        
        # Remove comments (// style)
        text = re.sub(r'//.*?(?=\n|$)', '', text)
        return text
    
    def _validate_structure(self, data: Union[List, Dict]) -> List[Dict]:
        """
        Validate the overall structure and extract questions.
        """
        questions = []
        
        if isinstance(data, list):
            # Direct list of questions
            questions = data
        elif isinstance(data, dict):
            # Check for common wrapper formats
            if 'questions' in data:
                questions = data['questions']
            elif all(str(k).isdigit() for k in data.keys()):
                # Numbered questions format: {"1": {...}, "2": {...}}
                questions = [data[k] for k in sorted(data.keys(), key=int)]
            else:
                # Check if this dict has the required fields to be a question
                required_fields = ['number', 'topic', 'pattern', 'question', 'answer']
                if any(field in data for field in required_fields):
                    # Single question object
                    questions = [data]
                else:
                    # Not a valid question structure
                    return []
        else:
            # Invalid structure - not list or dict
            return []
        
        # Ensure we return a list
        if not isinstance(questions, list):
            return []
        
        return questions
    
    def _validate_question(self, question: Dict, question_num: int) -> Dict[str, Any]:
        """
        Validate an individual question object.
        """
        result = {
            'is_valid': False,
            'question': None,
            'errors': [],
            'warnings': []
        }
        
        if not isinstance(question, dict):
            result['errors'].append(f"Question {question_num}: Must be an object, got {type(question)}")
            return result
        
        # Check required fields
        missing_fields = [field for field in self.required_fields if field not in question]
        if missing_fields:
            result['errors'].append(f"Question {question_num}: Missing required fields: {missing_fields}")
            return result
        
        # Validate and normalize fields
        normalized_question = {}
        
        # Validate number
        try:
            num = int(question['number'])
            if num <= 0:
                result['errors'].append(f"Question {question_num}: Number must be positive, got {num}")
                return result
            normalized_question['number'] = num
        except (ValueError, TypeError):
            result['errors'].append(f"Question {question_num}: 'number' must be an integer")
            return result
          # Validate topic
        topic = str(question['topic']).lower().strip()
        if topic not in self.valid_topics:
            result['warnings'].append(f"Question {question_num}: Unusual topic '{topic}'")
        normalized_question['topic'] = topic
        
        # Validate pattern
        pattern = str(question['pattern']).strip()
        if not pattern:
            result['errors'].append(f"Question {question_num}: Pattern cannot be empty")
            return result        # Check for mathematical symbols in pattern
        if not any(symbol in pattern for symbol in ['+', '-', '*', '/', '=', '_']):
            result['warnings'].append(f"Question {question_num}: Pattern '{pattern}' may not follow expected format")
        normalized_question['pattern'] = pattern
        
        # Validate question text
        question_text = str(question['question']).strip()
        if not question_text:
            result['errors'].append(f"Question {question_num}: Question text cannot be empty")
            return result        # Check for mathematical content in question
        if not any(symbol in question_text for symbol in ['+', '-', '*', '/', '=', '_']) and not any(char.isdigit() for char in question_text):
            result['warnings'].append(f"Question {question_num}: Question text may not be mathematical")
        normalized_question['question'] = question_text
        
        # Validate answer
        answer = question['answer']
        try:
            # Try to convert to number for math validation
            if isinstance(answer, str):
                # Remove common formatting
                clean_answer = answer.strip().replace(',', '')
                normalized_question['answer'] = float(clean_answer) if '.' in clean_answer else int(clean_answer)
            else:
                normalized_question['answer'] = float(answer) if isinstance(answer, (int, float)) else answer
        except (ValueError, TypeError):
            result['warnings'].append(f"Question {question_num}: Answer '{answer}' may not be numeric")
            normalized_question['answer'] = str(answer)
          # Additional validation: check mathematical consistency
        consistency_warning = self._validate_mathematical_consistency(
            normalized_question['question'], 
            normalized_question['answer'],
            question_num
        )
        if consistency_warning:
            result['warnings'].append(consistency_warning)
        
        result['is_valid'] = True
        result['question'] = normalized_question
        return result

    def _validate_mathematical_consistency(self, question_text: str, answer: Union[int, float, str], question_num: int) -> Optional[str]:
        """
        Check if the question and answer are mathematically consistent.
        """
        try:
            # Check for fill-in-the-blank questions with = sign
            if '_' in question_text and '=' in question_text and isinstance(answer, (int, float)):
                # Try to extract the mathematical operation
                # Pattern: "number operator _ = result" or "_ operator number = result"
                
                # For addition: a + _ = b, answer should be b - a
                add_match = re.search(r'(\d+)\s*\+\s*_\s*=\s*(\d+)', question_text)
                if add_match:
                    a, b = int(add_match.group(1)), int(add_match.group(2))
                    expected = b - a
                    if abs(answer - expected) > 0.001:  # Allow small floating point errors
                        return f"Question {question_num}: Answer doesn't match calculation - expected {expected}, got {answer}"
                
                # For subtraction: a - _ = b, answer should be a - b
                sub_match = re.search(r'(\d+)\s*-\s*_\s*=\s*(\d+)', question_text)
                if sub_match:
                    a, b = int(sub_match.group(1)), int(sub_match.group(2))
                    expected = a - b
                    if abs(answer - expected) > 0.001:
                        return f"Question {question_num}: Mathematical inconsistency - expected answer {expected}, got {answer}"
                
                # Check for unusually large answers
                if abs(answer) > 10000:
                    return f"Question {question_num}: Answer {answer} seems unusually large"
            
        except Exception:
            # If validation fails, don't report as error
            pass
        
        return None
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of validation results.
        """
        summary_lines = []
          # Basic stats
        total = validation_result['metadata']['total_questions']
        valid = validation_result['metadata']['valid_questions']
        summary_lines.append(f"Questions Found: {total}")
        
        # Status with expected format and symbols
        if validation_result['is_valid']:
            if validation_result.get('is_partial', False):
                summary_lines.append("Status: ✓ VALID (PARTIAL)")
            else:
                summary_lines.append("Status: ✓ VALID")
        else:
            summary_lines.append("Status: ✗ INVALID")
        
        # Errors
        if validation_result['errors']:
            summary_lines.append(f"Errors: {len(validation_result['errors'])}")
            for error in validation_result['errors'][:3]:  # Show first 3 errors
                summary_lines.append(f"  - {error}")
            if len(validation_result['errors']) > 3:
                summary_lines.append(f"  - ... and {len(validation_result['errors']) - 3} more")
        
        # Warnings
        if validation_result['warnings']:
            summary_lines.append(f"Warnings: {len(validation_result['warnings'])}")
            for warning in validation_result['warnings'][:2]:  # Show first 2 warnings
                summary_lines.append(f"  - {warning}")
            if len(validation_result['warnings']) > 2:
                summary_lines.append(f"  - ... and {len(validation_result['warnings']) - 2} more")
        
        return '\n'.join(summary_lines)
