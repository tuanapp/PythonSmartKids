# Example: How the notes field works in question patterns

# Before (old format):
patterns_old = [
    {
        "type": "decimal_addition",
        "pattern_text": "a + b = _"
    },
    {
        "type": "fraction_multiplication", 
        "pattern_text": "a × b = _"
    }
]

# After (with notes and level fields):
patterns_new = [
    {
        "type": "decimal_addition",
        "pattern_text": "a + b = _",
        "notes": "Answer should be formatted to 2 decimal places",
        "level": 3
    },
    {
        "type": "fraction_multiplication",
        "pattern_text": "a × b = _", 
        "notes": "Result should be in simplified fraction form (e.g., 1/2 not 2/4)",
        "level": 5
    },
    {
        "type": "percentage_calculation",
        "pattern_text": "a% of b = _",
        "notes": "Answer should include the % symbol",
        "level": 4
    },
    {
        "type": "basic_algebra",
        "pattern_text": "a + _ = b",
        "notes": None,  # No special formatting requirements
        "level": 2
    }
]

# Example: How level filtering works with the API

# API Request with level filtering:
request_data = {
    "uid": "student_123",
    "level": 3  # Only get patterns for level 3 (and NULL level)
}

# Database patterns available:
all_patterns = [
    {"type": "basic_addition", "pattern_text": "a + b = _", "level": 1},
    {"type": "double_digit_addition", "pattern_text": "a + b = _", "level": 2}, 
    {"type": "decimal_addition", "pattern_text": "a + b = _", "level": 3},
    {"type": "fraction_multiplication", "pattern_text": "a × b = _", "level": 5},
    {"type": "general_algebra", "pattern_text": "a + _ = b", "level": None}  # NULL level
]

# Patterns returned for level=3 request:
level_3_patterns = [
    {"type": "decimal_addition", "pattern_text": "a + b = _", "level": 3},
    {"type": "general_algebra", "pattern_text": "a + _ = b", "level": None}  # Included because level is NULL
]

# AI prompt will show:
# decimal_addition: a + b = _ [Level 3] (Notes: Answer should be formatted to 2 decimal places)
# general_algebra: a + _ = b
