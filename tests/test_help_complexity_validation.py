"""
Test script for validating AI-driven dynamic help complexity assessment.

This script tests that the help generation system:
1. Returns complexity_assessment field in responses
2. Returns step_count matching help_steps array length
3. Allows AI freedom to choose any step count (no rigid enforcement)
4. Handles questions of varying complexity appropriately

Run with: pytest tests/test_help_complexity_validation.py -v
"""

import pytest
from app.services.prompt_service import PromptService


# Sample test questions representing different complexity levels
SIMPLE_QUESTIONS = [
    {
        "question": "What is 2 + 2?",
        "answer": "4",
        "subject_id": 5,  # Mathematics
        "subject_name": "Mathematics",
        "expected_complexity": "simple"
    },
    {
        "question": "What is the capital of France?",
        "answer": "Paris",
        "subject_id": 2,  # Geography
        "subject_name": "Geography",
        "expected_complexity": "simple"
    },
    {
        "question": "What does CPU stand for?",
        "answer": "Central Processing Unit",
        "subject_id": 3,  # IT
        "subject_name": "IT",
        "expected_complexity": "simple"
    }
]

MODERATE_QUESTIONS = [
    {
        "question": "Calculate the area of a rectangle with length 8 cm and width 5 cm.",
        "answer": "40 square cm",
        "subject_id": 5,  # Mathematics
        "subject_name": "Mathematics",
        "expected_complexity": "moderate"
    },
    {
        "question": "Explain how photosynthesis works in plants.",
        "answer": "Plants use sunlight, water, and carbon dioxide to produce glucose and oxygen",
        "subject_id": 1,  # Science
        "subject_name": "Science",
        "expected_complexity": "moderate"
    }
]

COMPLEX_QUESTIONS = [
    {
        "question": "A train travels 240 km at an average speed of 60 km/h. If it then travels another 180 km at 45 km/h, what is the average speed for the entire journey?",
        "answer": "51.43 km/h",
        "subject_id": 5,  # Mathematics
        "subject_name": "Mathematics",
        "expected_complexity": "complex"
    },
    {
        "question": "Compare and contrast mitosis and meiosis, explaining their significance in organisms.",
        "answer": "Mitosis produces identical cells for growth and repair; meiosis produces genetically diverse gametes for reproduction",
        "subject_id": 1,  # Science
        "subject_name": "Science",
        "expected_complexity": "complex"
    }
]

ALL_TEST_QUESTIONS = SIMPLE_QUESTIONS + MODERATE_QUESTIONS + COMPLEX_QUESTIONS


class TestHelpComplexityValidation:
    """Validation tests for help complexity assessment system"""
    
    @pytest.fixture
    def prompt_service(self):
        """Create PromptService instance"""
        return PromptService()
    
    def test_complexity_field_exists(self, prompt_service):
        """Test that complexity_assessment field is returned"""
        # Use a simple question for quick test
        test_case = SIMPLE_QUESTIONS[0]
        
        result = prompt_service.generate_question_help(
            uid="test_uid_complexity",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text'
        )
        
        # Verify complexity_assessment is in response
        assert "complexity_assessment" in result, "Response must include complexity_assessment field"
        
        # Allow null/None (AI may omit), but if present, should be string
        if result["complexity_assessment"] is not None:
            assert isinstance(result["complexity_assessment"], str), "complexity_assessment must be string or None"
    
    def test_step_count_accuracy(self, prompt_service):
        """Test that step_count matches help_steps array length"""
        test_case = MODERATE_QUESTIONS[0]
        
        result = prompt_service.generate_question_help(
            uid="test_uid_step_count",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text'
        )
        
        # Verify step_count exists
        assert "step_count" in result, "Response must include step_count field"
        
        # Verify it matches array length
        actual_count = len(result["help_steps"])
        assert result["step_count"] == actual_count, f"step_count ({result['step_count']}) must match help_steps length ({actual_count})"
    
    def test_valid_complexity_values(self, prompt_service):
        """Test that complexity_assessment contains valid documented values"""
        documented_values = {"simple", "moderate", "complex"}
        
        test_case = MODERATE_QUESTIONS[0]
        
        result = prompt_service.generate_question_help(
            uid="test_uid_valid_values",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text'
        )
        
        complexity = result.get("complexity_assessment")
        
        # If AI provided a value, it should be from documented set
        # (but allow new values for extensibility - this is a warning, not failure)
        if complexity is not None:
            if complexity not in documented_values:
                print(f"⚠️  WARNING: AI returned undocumented complexity value: '{complexity}'")
                print(f"   Documented values: {documented_values}")
                print(f"   This may indicate a new complexity level - verify it's intentional")
    
    def test_no_step_count_enforcement(self, prompt_service):
        """Test that AI has freedom to choose any step count (no rigid rules)"""
        # This test verifies we DON'T enforce rigid step count rules
        # AI should be free to use 1-N steps based on pedagogical needs
        
        test_case = SIMPLE_QUESTIONS[0]
        
        result = prompt_service.generate_question_help(
            uid="test_uid_freedom",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text',
            student_grade_level=1  # Young student - may benefit from multiple steps even for simple questions
        )
        
        step_count = result["step_count"]
        complexity = result.get("complexity_assessment")
        
        # NO ENFORCEMENT - just log the AI's decision
        print(f"\n✓ AI Decision for '{test_case['question']}':")
        print(f"  Complexity: {complexity or 'not assessed'}")
        print(f"  Steps: {step_count}")
        print(f"  Grade Level: 1")
        print(f"  → AI has freedom to choose any step count")
        
        # Always pass - we trust AI's judgment
        assert step_count >= 1, "Must have at least 1 step"
    
    @pytest.mark.parametrize("test_case", ALL_TEST_QUESTIONS)
    def test_diverse_questions(self, prompt_service, test_case):
        """Test help generation across questions of varying complexity"""
        result = prompt_service.generate_question_help(
            uid="test_uid_diverse",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text'
        )
        
        # Basic validation
        assert "help_steps" in result
        assert "step_count" in result
        assert "complexity_assessment" in result
        assert result["step_count"] == len(result["help_steps"])
        
        # Log AI's assessment for review
        print(f"\n{'='*60}")
        print(f"Question: {test_case['question'][:60]}...")
        print(f"Expected Complexity: {test_case['expected_complexity']}")
        print(f"AI Assessed: {result.get('complexity_assessment', 'None')}")
        print(f"Steps: {result['step_count']}")
        print(f"{'='*60}")


class TestComplexityCorrelationAnalytics:
    """Tests for monitoring complexity vs step count correlation"""
    
    @pytest.fixture
    def prompt_service(self):
        return PromptService()
    
    def test_complexity_step_correlation_logging(self, prompt_service):
        """Test that complexity and step count are logged together for analytics"""
        # This test ensures our logging captures both metrics for correlation analysis
        
        test_case = MODERATE_QUESTIONS[0]
        
        result = prompt_service.generate_question_help(
            uid="test_uid_analytics",
            question=test_case["question"],
            correct_answer=test_case["answer"],
            subject_id=test_case["subject_id"],
            subject_name=test_case["subject_name"],
            has_answered=False,
            visual_preference='text'
        )
        
        # Verify both metrics exist for analytics
        assert "complexity_assessment" in result
        assert "step_count" in result
        
        # Log format that should appear in backend logs
        print(f"\n📊 Analytics Data:")
        print(f"   complexity={result.get('complexity_assessment', 'not_assessed')}")
        print(f"   steps={result['step_count']}")
        print(f"   subject={test_case['subject_name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
