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

# After (with notes field):
patterns_new = [
    {
        "type": "decimal_addition",
        "pattern_text": "a + b = _",
        "notes": "Answer should be formatted to 2 decimal places"
    },
    {
        "type": "fraction_multiplication",
        "pattern_text": "a × b = _", 
        "notes": "Result should be in simplified fraction form (e.g., 1/2 not 2/4)"
    },
    {
        "type": "percentage_calculation",
        "pattern_text": "a% of b = _",
        "notes": "Answer should include the % symbol"
    },
    {
        "type": "basic_algebra",
        "pattern_text": "a + _ = b",
        "notes": None  # No special formatting requirements
    }
]

# How it appears in the AI prompt:
# decimal_addition: a + b = _ (Notes: Answer should be formatted to 2 decimal places)
# fraction_multiplication: a × b = _ (Notes: Result should be in simplified fraction form (e.g., 1/2 not 2/4))
# percentage_calculation: a% of b = _ (Notes: Answer should include the % symbol)
# basic_algebra: a + _ = b
