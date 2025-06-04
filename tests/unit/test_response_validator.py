"""
Comprehensive test suite for the OpenAI response validator.
Tests validation of AI responses for proper format adherence.
"""

import pytest
import json
from app.validators.response_validator import OpenAIResponseValidator


class TestOpenAIResponseValidator:
    """Test suite for OpenAI response validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = OpenAIResponseValidator()

    def test_valid_response_complete(self):
        """Test validation of a complete, valid response."""
        valid_response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            },
            {
                "number": 2,
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "10 - _ = 3",
                "answer": 7
            }
        ])

        result = self.validator.validate_response(valid_response)

        assert result['is_valid'] is True
        assert len(result['questions']) == 2
        assert len(result['errors']) == 0
        assert result['questions'][0]['number'] == 1
        assert result['questions'][1]['topic'] == 'subtraction'

    def test_valid_response_with_markdown_wrapper(self):
        """Test validation with markdown code block formatting."""
        markdown_response = """```json
        [
            {
                "number": 1,
                "topic": "multiplication",
                "pattern": "a × _ = b",
                "question": "6 × _ = 24",
                "answer": 4
            }
        ]
        ```"""

        result = self.validator.validate_response(markdown_response)

        assert result['is_valid'] is True
        assert len(result['questions']) == 1
        assert result['questions'][0]['answer'] == 4

    def test_valid_response_questions_wrapper(self):
        """Test validation with questions wrapper format."""
        wrapped_response = json.dumps({
            "questions": [
                {
                    "number": 1,
                    "topic": "division",
                    "pattern": "a ÷ _ = b",
                    "question": "20 ÷ _ = 4",
                    "answer": 5
                }
            ]
        })

        result = self.validator.validate_response(wrapped_response)

        assert result['is_valid'] is True
        assert len(result['questions']) == 1
        assert result['questions'][0]['topic'] == 'division'

    def test_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        invalid_response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                # Missing pattern, question, answer
            }
        ])

        result = self.validator.validate_response(invalid_response)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any("Missing required fields" in error for error in result['errors'])

    def test_invalid_data_types(self):
        """Test validation fails with invalid data types."""
        invalid_response = json.dumps([
            {
                "number": "not_a_number",  # Should be int
                "topic": 123,  # Should be string
                "pattern": None,  # Should be string
                "question": "",  # Should not be empty
                "answer": None  # Should not be null
            }
        ])

        result = self.validator.validate_response(invalid_response)

        assert result['is_valid'] is False
        assert len(result['errors']) >= 1  # At least one error for invalid fields

    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        malformed_json = """[
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3,  // Invalid trailing comma
            }
        ]"""

        result = self.validator.validate_response(malformed_json)

        assert result['is_valid'] is False
        assert any("JSON parsing failed" in error for error in result['errors'])

    def test_empty_response(self):
        """Test handling of empty response."""
        result = self.validator.validate_response("")
        
        assert result['is_valid'] is False
        assert any("Empty or null response" in error for error in result['errors'])

    def test_non_list_response(self):
        """Test handling of non-list response format."""
        non_list_response = json.dumps({
            "message": "This is not a list of questions"
        })

        result = self.validator.validate_response(non_list_response)

        assert result['is_valid'] is False
        assert any("Expected list" in error or "contains no questions" in error for error in result['errors'])

    def test_mathematical_consistency_addition(self):
        """Test mathematical consistency validation for addition."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3  # Correct: 8 - 5 = 3
            },
            {
                "number": 2,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "10 + _ = 15",
                "answer": 10  # Incorrect: should be 5
            }
        ])

        result = self.validator.validate_response(response)

        # Should still be valid but with warnings about math inconsistency
        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert any("doesn't match calculation" in warning for warning in result['warnings'])

    def test_mathematical_consistency_subtraction(self):
        """Test mathematical consistency validation for subtraction."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "10 - _ = 3",
                "answer": 7  # Correct: 10 - 3 = 7
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        # Should have no math consistency warnings for correct answer
        math_warnings = [w for w in result['warnings'] if "doesn't match calculation" in w]
        assert len(math_warnings) == 0

    def test_partial_validation_success(self):
        """Test partial validation with mix of valid and invalid questions."""
        mixed_response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            },
            {
                "number": "invalid",  # Invalid number field
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "10 - _ = 3",
                "answer": 7
            },
            {
                "number": 3,
                "topic": "multiplication",
                "pattern": "a × _ = b",
                "question": "6 × _ = 24",
                "answer": 4
            }
        ])

        result = self.validator.validate_partial_response(mixed_response, min_questions=2)

        assert result['is_valid'] is True
        assert result.get('is_partial') is True
        assert len(result['questions']) == 2  # Two valid questions

    def test_partial_validation_failure(self):
        """Test partial validation failure when not enough valid questions."""
        mostly_invalid_response = json.dumps([
            {
                "number": "invalid",
                "topic": "addition"
                # Missing required fields
            },
            {
                "number": 2,
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "10 - _ = 3",
                "answer": 7
            }
        ])

        result = self.validator.validate_partial_response(mostly_invalid_response, min_questions=2)

        assert result['is_valid'] is False
        assert len(result['questions']) == 1  # Only one valid question

    def test_topic_validation_warnings(self):
        """Test validation warnings for unusual topics."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "quantum_physics",  # Unusual topic
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert any("Unusual topic" in warning for warning in result['warnings'])

    def test_pattern_validation_warnings(self):
        """Test validation warnings for unusual patterns."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "unusual pattern format",  # No standard symbols
                "question": "5 + _ = 8",
                "answer": 3
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert any("may not follow expected format" in warning for warning in result['warnings'])

    def test_question_validation_warnings(self):
        """Test validation warnings for non-mathematical questions."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "What is your favorite color?",  # No math symbols
                "answer": "blue"
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert any("may not be mathematical" in warning for warning in result['warnings'])

    def test_string_answer_handling(self):
        """Test handling of string answers."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "algebra",
                "pattern": "solve for x",
                "question": "What is x in x + 2 = 5?",
                "answer": "3"  # String answer that can be converted to number
            },
            {
                "number": 2,
                "topic": "algebra",
                "pattern": "solve for y",
                "question": "What is y in 2y = 10?",
                "answer": "five"  # String answer that stays as string
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert result['questions'][0]['answer'] == 3  # Converted to int
        assert result['questions'][1]['answer'] == "five"  # Kept as string

    def test_float_answer_handling(self):
        """Test handling of float answers."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "division",
                "pattern": "a ÷ b = _",
                "question": "10 ÷ 3 = ?",
                "answer": 3.33
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert result['questions'][0]['answer'] == 3.33

    def test_large_response_warning(self):
        """Test warning for unusually large responses."""
        large_response = json.dumps([
            {
                "number": i,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": f"{i} + _ = {i+5}",
                "answer": 5
            }
            for i in range(1, 52)  # 51 questions (over the 50 limit)
        ])

        result = self.validator.validate_response(large_response)

        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert any("unusually high" in warning for warning in result['warnings'])

    def test_validation_summary_valid(self):
        """Test validation summary for valid response."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            }
        ])

        result = self.validator.validate_response(response)
        summary = self.validator.get_validation_summary(result)

        assert "✓ VALID" in summary
        assert "Questions Found: 1" in summary

    def test_validation_summary_invalid(self):
        """Test validation summary for invalid response."""
        result = self.validator.validate_response("invalid json")
        summary = self.validator.get_validation_summary(result)

        assert "✗ INVALID" in summary
        assert "Errors:" in summary

    def test_validation_summary_partial(self):
        """Test validation summary for partial response."""
        mixed_response = json.dumps([
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            },
            {
                "number": "invalid"
                # Missing other required fields
            }
        ])

        result = self.validator.validate_partial_response(mixed_response, min_questions=1)
        summary = self.validator.get_validation_summary(result)

        assert "✓ VALID (PARTIAL)" in summary

    def test_json_formatting_fix(self):
        """Test automatic fixing of common JSON formatting issues."""
        malformed_response = """[
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3,
            },
            {
                "number": 2,
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "10 - _ = 3",
                "answer": 7,
            },
        ]"""

        result = self.validator.validate_response(malformed_response)

        # Should successfully parse after fixing trailing commas
        assert result['is_valid'] is True
        assert len(result['questions']) == 2

    def test_different_response_wrappers(self):
        """Test handling of different response wrapper formats."""
        # Test "Here is the JSON:" wrapper
        wrapped_response1 = """Here is the JSON response:
        [{"number": 1, "topic": "addition", "pattern": "a + _ = b", "question": "5 + _ = 8", "answer": 3}]"""

        result1 = self.validator.validate_response(wrapped_response1)
        assert result1['is_valid'] is True

        # Test "Response:" wrapper
        wrapped_response2 = """Response:
        [{"number": 1, "topic": "addition", "pattern": "a + _ = b", "question": "5 + _ = 8", "answer": 3}]"""

        result2 = self.validator.validate_response(wrapped_response2)
        assert result2['is_valid'] is True

    def test_edge_cases(self):
        """Test various edge cases."""
        # Empty list
        empty_list = json.dumps([])
        result = self.validator.validate_response(empty_list)
        assert result['is_valid'] is False
        assert any("contains no questions" in error for error in result['errors'])

        # Null response
        result = self.validator.validate_response(None)
        assert result['is_valid'] is False

        # Very long strings
        long_response = json.dumps([{
            "number": 1,
            "topic": "addition" * 100,  # Very long topic
            "pattern": "a + _ = b",
            "question": "5 + _ = 8",
            "answer": 3
        }])

        result = self.validator.validate_response(long_response)
        assert result['is_valid'] is True  # Should handle long strings

    def test_negative_numbers(self):
        """Test handling of negative numbers."""
        response = json.dumps([
            {
                "number": -1,  # Invalid negative number
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            },
            {
                "number": 1,
                "topic": "subtraction",
                "pattern": "a - _ = b",
                "question": "5 - _ = 8",
                "answer": -3  # Valid negative answer
            }
        ])

        result = self.validator.validate_response(response)

        # First question should be invalid due to negative number
        # Second question should be valid with negative answer
        assert len(result['questions']) == 1  # Only one valid question
        assert result['questions'][0]['answer'] == -3

    def test_zero_values(self):
        """Test handling of zero values."""
        response = json.dumps([
            {
                "number": 0,  # Invalid zero number
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 8",
                "answer": 3
            },
            {
                "number": 1,
                "topic": "addition",
                "pattern": "a + _ = b",
                "question": "5 + _ = 5",
                "answer": 0  # Valid zero answer
            }
        ])

        result = self.validator.validate_response(response)

        # First question should be invalid due to zero number
        # Second question should be valid with zero answer
        assert len(result['questions']) == 1
        assert result['questions'][0]['answer'] == 0

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special mathematical characters."""
        response = json.dumps([
            {
                "number": 1,
                "topic": "multiplication",
                "pattern": "a × _ = b",  # Unicode multiplication symbol
                "question": "5 × _ = 20",
                "answer": 4
            },
            {
                "number": 2,
                "topic": "division",
                "pattern": "a ÷ _ = b",  # Unicode division symbol
                "question": "20 ÷ _ = 4",
                "answer": 5
            }
        ])

        result = self.validator.validate_response(response)

        assert result['is_valid'] is True
        assert len(result['questions']) == 2
        assert "×" in result['questions'][0]['pattern']
        assert "÷" in result['questions'][1]['pattern']
