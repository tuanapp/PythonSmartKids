"""
Verify taxonomy improvements based on actual questions.
Shows before/after comparison of coverage.
"""
from app.services.subject_taxonomy import SUBJECT_TAXONOMY

# Sample questions that were previously uncategorizable
test_cases = [
    # Science - Pollination (was "General concept")
    {
        "subject": "Science",
        "question": "What is the difference between self-pollination and cross-pollination?",
        "expected_topic": "Plant Life",
        "expected_concept": "Self-pollination vs cross-pollination"
    },
    {
        "subject": "Science",
        "question": "How do flowers attract pollinators?",
        "expected_topic": "Plant Life",
        "expected_concept": "Attracting pollinators"
    },
    # French - Reflexive verbs (was "Uncategorized")
    {
        "subject": "French",
        "question": "What is the correct conjugation of s'appeler for je?",
        "expected_topic": "Grammar → Verbs",
        "expected_concept": "Reflexive verbs"
    },
    # Geography - Administrative (was "General")
    {
        "subject": "Geography",
        "question": "What is the smallest administrative unit in Sri Lanka?",
        "expected_topic": "Political Geography → Administrative Divisions",
        "expected_concept": "Grama Niladhari Division"
    },
    {
        "subject": "Geography",
        "question": "How do you find direction using the sun?",
        "expected_topic": "Political Geography → Map Skills & Directions",
        "expected_concept": "Finding directions without compass"
    },
    # IT - Robotics (was "General concept")
    {
        "subject": "IT",
        "question": "What is the main purpose of robots in manufacturing?",
        "expected_topic": "Inventions & Innovation → Robotics & AI",
        "expected_concept": "Robots in manufacturing"
    },
    # Math - Ratios (was sometimes "General")
    {
        "subject": "Math",
        "question": "A recipe calls for 2 cups flour to 1 cup sugar. How much sugar for 6 cups flour?",
        "expected_topic": "Fractions & Decimals → Ratios & Proportions",
        "expected_concept": "Recipe and mixture problems"
    },
    # English - Adjective order (was "General concept")
    {
        "subject": "English",
        "question": "What is the correct order of adjectives in 'the big red car'?",
        "expected_topic": "Grammar → Parts of Speech",
        "expected_concept": "Adjective order"
    }
]

def check_taxonomy_coverage():
    """Check if expected concepts exist in taxonomy."""
    print("="*80)
    print("TAXONOMY IMPROVEMENT VERIFICATION")
    print("="*80)
    print("\nChecking if problematic questions now have specific taxonomy coverage:\n")
    
    success_count = 0
    for i, test in enumerate(test_cases, 1):
        subject = test["subject"]
        question = test["question"][:70] + "..." if len(test["question"]) > 70 else test["question"]
        expected = test["expected_concept"]
        
        # Check if subject exists
        if subject not in SUBJECT_TAXONOMY:
            print(f"{i}. ✗ FAIL: Subject '{subject}' not in taxonomy")
            print(f"   Question: {question}")
            continue
        
        # Search for concept in taxonomy
        found = False
        found_location = ""
        for topic, subtopics in SUBJECT_TAXONOMY[subject].items():
            for subtopic, concepts in subtopics.items():
                # Check if expected concept appears in the concepts list
                for concept in concepts:
                    if expected.lower() in concept.lower():
                        found = True
                        found_location = f"{topic} → {subtopic} → {concept}"
                        break
                if found:
                    break
            if found:
                break
        
        if found:
            print(f"{i}. ✓ PASS: Found coverage")
            print(f"   Question: {question}")
            print(f"   Location: {found_location}")
            success_count += 1
        else:
            print(f"{i}. ✗ FAIL: Concept '{expected}' not found")
            print(f"   Question: {question}")
            print(f"   Subject: {subject}")
    
    print(f"\n{'='*80}")
    print(f"RESULTS: {success_count}/{len(test_cases)} test cases passed")
    print(f"{'='*80}")
    
    if success_count == len(test_cases):
        print("\n🎉 SUCCESS! All problematic questions now have specific taxonomy coverage!")
        print("The categorization should now avoid 'General' and 'Uncategorized' labels.")
    else:
        print(f"\n⚠️  {len(test_cases) - success_count} test case(s) still need coverage.")

if __name__ == "__main__":
    check_taxonomy_coverage()
