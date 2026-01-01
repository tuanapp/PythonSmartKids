from app.services.subject_taxonomy import SUBJECT_TAXONOMY

print('Taxonomy subjects:', list(SUBJECT_TAXONOMY.keys()))
print('\nDatabase subjects mapping test:')

# Test all database subjects (now all lowercase)
database_subjects = [
    'maths',  # id:5
    'english',  # id:2
    'science',  # id:1
    'french',  # id:3
    'sinhala',  # id:8
    'geography',  # id:4
    'history',  # id:7
    'it'  # id:6
]

subject_mapping = {
    # Math variations
    "Maths": "Math",
    "Math": "Math",
    "Mathematics": "Math",
    # English
    "English": "English",
    # Science
    "Science": "Science",
    # History
    "History": "History",
    # Geography  
    "Geography": "Geography",
    # Nature
    "Nature": "Nature",
    # Space
    "Space": "Space",
    # Technology and IT variations
    "Technology": "Technology",
    "It Technology": "Technology",
    "It": "IT",
    "Information Technology": "IT",
    "Computer": "IT",
    # French
    "French": "French",
    "French-T1": "French",
    # Sinhala
    "Sinhala": "Sinhala",
    # General Knowledge
    "General Knowledge": "General Knowledge",
    "Gk": "General Knowledge"
}

for db_subject in database_subjects:
    normalized = db_subject.strip().title()
    taxonomy_key = subject_mapping.get(normalized, normalized)
    exists = taxonomy_key in SUBJECT_TAXONOMY
    status = "✓" if exists else "✗ MISSING"
    print(f'  {db_subject:15} -> {normalized:20} -> {taxonomy_key:20} {status}')

print('\nTaxonomy coverage:')
for subject_key in SUBJECT_TAXONOMY.keys():
    print(f'  {subject_key}: {len(SUBJECT_TAXONOMY[subject_key])} topics')
