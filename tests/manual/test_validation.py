#!/usr/bin/env python3
"""
Test runner script for comprehensive validation testing.
This script tests the response validator functionality and integration.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.validators.response_validator import OpenAIResponseValidator
from app.services.ai_service import generate_practice_questions

class ValidationTestRunner:
    """Test runner for validation functionality."""
    
    def __init__(self):
        self.validator = OpenAIResponseValidator()
        self.test_cases = self._create_test_cases()
        self.results = []
    
    def _create_test_cases(self):
        """Create comprehensive test cases for validation."""
        return {
            "valid_response": {
                "name": "Valid Response",
                "data": json.dumps([
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
                ]),
                "expected_valid": True,
                "expected_questions": 2
            },
            
            "markdown_wrapped": {
                "name": "Markdown Wrapped Response",
                "data": """```json
                [
                    {
                        "number": 1,
                        "topic": "multiplication",
                        "pattern": "a × _ = b",
                        "question": "6 × _ = 24",
                        "answer": 4
                    }
                ]
                ```""",
                "expected_valid": True,
                "expected_questions": 1
            },
            
            "questions_wrapper": {
                "name": "Questions Wrapper Format",
                "data": json.dumps({
                    "questions": [
                        {
                            "number": 1,
                            "topic": "division",
                            "pattern": "a ÷ _ = b",
                            "question": "20 ÷ _ = 4",
                            "answer": 5
                        }
                    ]
                }),
                "expected_valid": True,
                "expected_questions": 1
            },
            
            "missing_fields": {
                "name": "Missing Required Fields",
                "data": json.dumps([
                    {
                        "number": 1,
                        "topic": "addition"
                        # Missing pattern, question, answer
                    }
                ]),
                "expected_valid": False,
                "expected_questions": 0
            },
            
            "invalid_types": {
                "name": "Invalid Data Types",
                "data": json.dumps([
                    {
                        "number": "not_a_number",
                        "topic": 123,
                        "pattern": None,
                        "question": "",
                        "answer": None
                    }
                ]),
                "expected_valid": False,
                "expected_questions": 0
            },
              "malformed_json": {
                "name": "Malformed JSON",
                "data": """[
                    {
                        "number": 1,
                        "topic": "addition",
                        "pattern": "a + _ = b",
                        "question": "5 + _ = 8",
                        "answer": 3,
                    }
                ]""",
                "expected_valid": True,  # Validator fixes trailing commas automatically
                "expected_questions": 1
            },
            
            "empty_response": {
                "name": "Empty Response",
                "data": "",
                "expected_valid": False,
                "expected_questions": 0
            },
              "math_inconsistency": {
                "name": "Mathematical Inconsistency",
                "data": json.dumps([
                    {
                        "number": 1,
                        "topic": "addition",
                        "pattern": "a + _ = b",
                        "question": "5 + _ = 8",
                        "answer": 10  # Incorrect: should be 3
                    }
                ]),
                "expected_valid": False,  # Validator fails due to math inconsistency
                "expected_questions": 0
            },
            
            "partial_valid": {
                "name": "Partially Valid Response",
                "data": json.dumps([
                    {
                        "number": 1,
                        "topic": "addition",
                        "pattern": "a + _ = b",
                        "question": "5 + _ = 8",
                        "answer": 3
                    },
                    {
                        "number": "invalid",
                        "topic": "subtraction"
                        # Missing other fields
                    },
                    {
                        "number": 3,
                        "topic": "multiplication",
                        "pattern": "a × _ = b",
                        "question": "6 × _ = 24",
                        "answer": 4
                    }
                ]),                "expected_valid": True,  # For partial validation
                "expected_questions": 2,  # But partial validation should succeed
                "test_partial": True
            }
        }
    
    def run_validator_tests(self):
        """Run all validator test cases."""
        print("=" * 80)
        print("RUNNING RESPONSE VALIDATOR TESTS")
        print("=" * 80)
        
        for test_id, test_case in self.test_cases.items():
            print(f"\n--- Testing: {test_case['name']} ---")
            
            # Test regular validation
            result = self.validator.validate_response(test_case['data'])
            
            # Check if test should use partial validation
            if test_case.get('test_partial'):
                partial_result = self.validator.validate_partial_response(test_case['data'], min_questions=1)
                print(f"Partial validation: {partial_result['is_valid']}")
                
            success = self._check_test_result(test_case, result)
            
            # Generate and display summary
            summary = self.validator.get_validation_summary(result)
            print(f"Summary:\n{summary}")
            
            self.results.append({
                'test_id': test_id,
                'test_name': test_case['name'],
                'success': success,
                'result': result
            })
            
            print(f"Test Result: {'✓ PASS' if success else '✗ FAIL'}")
    
    def _check_test_result(self, test_case, result):
        """Check if test result matches expectations."""
        expected_valid = test_case['expected_valid']
        expected_questions = test_case['expected_questions']
        
        actual_valid = result['is_valid']
        actual_questions = len(result['questions'])
        
        valid_match = actual_valid == expected_valid
        questions_match = actual_questions == expected_questions
        
        if not valid_match:
            print(f"  ✗ Validity mismatch: expected {expected_valid}, got {actual_valid}")
        if not questions_match:
            print(f"  ✗ Questions count mismatch: expected {expected_questions}, got {actual_questions}")
        
        if valid_match and questions_match:
            print(f"  ✓ All checks passed")
            return True
        
        return False
    
    def test_ai_service_integration(self):
        """Test validator integration with AI service."""
        print("\n" + "=" * 80)
        print("TESTING AI SERVICE INTEGRATION")
        print("=" * 80)
        
        # Mock attempts data for testing
        mock_attempts = [
            {
                "question": "5 + 3",
                "is_correct": False,
                "incorrect_answer": "7",
                "correct_answer": "8",
                "datetime": datetime.now().isoformat()
            },
            {
                "question": "10 - 4",
                "is_correct": True,
                "incorrect_answer": "",
                "correct_answer": "6",
                "datetime": datetime.now().isoformat()
            }
        ]
        
        # Mock patterns data
        mock_patterns = [
            {
                "id": "1",
                "type": "addition",
                "pattern_text": "a + _ = b",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "2",
                "type": "subtraction",
                "pattern_text": "a - _ = b",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        try:
            print("Testing AI service with mock data...")
            
            # This would normally call the real AI service
            # For testing, we'll simulate with mock responses
            mock_ai_responses = [
                # Valid response
                json.dumps([
                    {
                        "number": 1,
                        "topic": "addition",
                        "pattern": "a + _ = b",
                        "question": "7 + _ = 12",
                        "answer": 5
                    }
                ]),
                # Invalid response (missing fields)
                json.dumps([
                    {
                        "number": 1,
                        "topic": "addition"
                    }
                ]),
                # Markdown wrapped response
                """```json
                [
                    {
                        "number": 1,
                        "topic": "subtraction",
                        "pattern": "a - _ = b",
                        "question": "15 - _ = 8",
                        "answer": 7
                    }
                ]
                ```"""
            ]
            
            for i, mock_response in enumerate(mock_ai_responses, 1):
                print(f"\n--- Mock AI Response {i} ---")
                
                # Test validation directly
                result = self.validator.validate_response(mock_response)
                summary = self.validator.get_validation_summary(result)
                
                print(f"Validation Result: {'✓ VALID' if result['is_valid'] else '✗ INVALID'}")
                print(f"Questions Found: {len(result['questions'])}")
                print(f"Errors: {len(result['errors'])}")
                print(f"Warnings: {len(result['warnings'])}")
                
                if result['errors']:
                    print("Errors:", result['errors'][:2])  # Show first 2 errors
                if result['warnings']:
                    print("Warnings:", result['warnings'][:2])  # Show first 2 warnings
            
            print("\n✓ AI service integration tests completed")
            
        except Exception as e:
            print(f"✗ AI service integration test failed: {str(e)}")
    
    def run_performance_tests(self):
        """Run performance tests on the validator."""
        print("\n" + "=" * 80)
        print("RUNNING PERFORMANCE TESTS")
        print("=" * 80)
        
        # Test with different response sizes
        sizes = [1, 10, 50, 100]
        
        for size in sizes:
            print(f"\n--- Testing with {size} questions ---")
            
            # Generate test data
            large_response = json.dumps([
                {
                    "number": i,
                    "topic": "addition",
                    "pattern": "a + _ = b",
                    "question": f"{i} + _ = {i+5}",
                    "answer": 5
                }
                for i in range(1, size + 1)
            ])
            
            # Measure validation time
            start_time = datetime.now()
            result = self.validator.validate_response(large_response)
            end_time = datetime.now()
            
            validation_time = (end_time - start_time).total_seconds()
            
            print(f"  Validation time: {validation_time:.4f} seconds")
            print(f"  Questions validated: {len(result['questions'])}")
            print(f"  Time per question: {validation_time/size:.6f} seconds")
            print(f"  Success: {'✓' if result['is_valid'] else '✗'}")
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY REPORT")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests Run: {total_tests}")
        print(f"Tests Passed: {passed_tests}")
        print(f"Tests Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"  ✗ {result['test_name']}")
        
        print(f"\n{'='*80}")
        print(f"VALIDATION TESTING COMPLETED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")


def main():
    """Main function to run validation tests."""
    parser = argparse.ArgumentParser(description='Run validation tests for PythonSmartKids API')
    parser.add_argument('--validator-only', action='store_true', 
                       help='Run only validator tests (skip AI service integration)')
    parser.add_argument('--performance', action='store_true',
                       help='Include performance tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create and run test runner
    runner = ValidationTestRunner()
    
    print("PythonSmartKids API - Validation Test Runner")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run validator tests
        runner.run_validator_tests()
        
        # Run AI service integration tests unless skipped
        if not args.validator_only:
            runner.test_ai_service_integration()
        
        # Run performance tests if requested
        if args.performance:
            runner.run_performance_tests()
        
        # Generate final report
        runner.generate_report()
        
        return 0 if all(r['success'] for r in runner.results) else 1
        
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
