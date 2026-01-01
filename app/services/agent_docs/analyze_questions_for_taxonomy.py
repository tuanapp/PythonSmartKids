"""
Analyze actual student question attempts to improve subject taxonomy.
"""
import json
from collections import defaultdict
from app.services.subject_taxonomy import SUBJECT_TAXONOMY

def analyze_questions(json_file_path):
    """Analyze questions and suggest taxonomy improvements."""
    
    # Load questions
    with open(json_file_path, 'r', encoding='utf-8') as f:
        attempts = json.load(f)
    
    # Group by subject
    subject_questions = defaultdict(list)
    for attempt in attempts:
        subject_id = attempt.get('subject_id')
        question = attempt.get('question', '')
        
        # Map subject_id to subject name (based on the JSON you shared)
        subject_map = {
            1: 'science',
            2: 'english', 
            3: 'french',
            4: 'geography',
            5: 'maths',
            6: 'it',
            7: 'history',
            8: 'sinhala'
        }
        
        subject_name = subject_map.get(subject_id, f'unknown_{subject_id}')
        subject_questions[subject_name].append({
            'question': question,
            'user_answer': attempt.get('user_answer'),
            'correct_answer': attempt.get('correct_answer'),
            'evaluation_status': attempt.get('evaluation_status')
        })
    
    # Print analysis
    print("=" * 80)
    print("QUESTION ANALYSIS FOR TAXONOMY IMPROVEMENT")
    print("=" * 80)
    print()
    
    for subject, questions in sorted(subject_questions.items()):
        subject_title = subject.title()
        
        # Map to taxonomy key
        subject_mapping = {
            'Maths': 'Math',
            'English': 'English',
            'Science': 'Science',
            'French': 'French',
            'Sinhala': 'Sinhala',
            'Geography': 'Geography',
            'History': 'History',
            'It': 'IT'
        }
        taxonomy_key = subject_mapping.get(subject_title, subject_title)
        
        print(f"\n{'='*80}")
        print(f"SUBJECT: {subject_title.upper()} (Database: {subject}, Taxonomy: {taxonomy_key})")
        print(f"Total Questions: {len(questions)}")
        print(f"{'='*80}")
        
        # Show current taxonomy
        if taxonomy_key in SUBJECT_TAXONOMY:
            print(f"\nCurrent Taxonomy:")
            for topic, subtopics in SUBJECT_TAXONOMY[taxonomy_key].items():
                print(f"  • {topic}")
                for subtopic in subtopics.keys():
                    print(f"      - {subtopic}")
        else:
            print(f"\n⚠️  NO TAXONOMY FOUND FOR {taxonomy_key}")
        
        print(f"\nSample Questions (first 20):")
        for i, q in enumerate(questions[:20], 1):
            question_text = q['question'][:100]
            if len(q['question']) > 100:
                question_text += "..."
            print(f"  {i}. {question_text}")
        
        if len(questions) > 20:
            print(f"\n  ... and {len(questions) - 20} more questions")
        
        print()
    
    # Suggestions section
    print("\n" + "="*80)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*80)
    print("\nBased on the questions above, please manually identify:")
    print("1. Topics/concepts that appear frequently but aren't in the taxonomy")
    print("2. Areas where subtopics should be split for more granularity")
    print("3. New concepts to add to existing subtopics")
    print("\nPaste all questions into an LLM to get automated analysis if needed.")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_questions_for_taxonomy.py <path_to_json_file>")
        print("\nExample:")
        print('  python analyze_questions_for_taxonomy.py "d:\\_downloads\\knowledge_question_attempts (2).json"')
        sys.exit(1)
    
    json_file = sys.argv[1]
    analyze_questions(json_file)
