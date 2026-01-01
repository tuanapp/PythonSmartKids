# Taxonomy Improvements Based on Actual Student Questions

## Analysis Summary

After analyzing 261 actual student question attempts across 8 subjects, the following improvements are recommended:

---

## 1. **ENGLISH** (63 questions analyzed)

### Current Gaps Identified:
- **Adjective order** appears in 8+ questions but not explicitly in taxonomy
- **Adverb placement** and **word function identification** appear frequently

### Recommended Changes:

**ENHANCE: Grammar → Parts of Speech**
- ADD concepts: "Adjective order (opinion-size-age-shape-color-origin-material-purpose)"
- ADD concepts: "Adverb placement and function"
- CURRENT: "Adjectives", "Adverbs"
- IMPROVED: "Adjectives", "Adjective order", "Adverbs", "Adverb placement and function"

**ENHANCE: Grammar → Tenses**
- ADD concept: "Tense consistency and subject-verb agreement"
- Sample questions show focus on present perfect tense and verb forms

**ENHANCE: Grammar → Sentence Structure**
- ADD concept: "Verb forms and conjugation"

---

## 2. **FRENCH** (36 questions analyzed)

### Current Gaps Identified:
- **Reflexive verbs** (s'appeler) appear in 6+ questions - NOT in current taxonomy
- **Digital vocabulary** (website, mouse, email) appears frequently
- **Numbers** (0-100) tested but not in taxonomy

### Recommended Changes:

**ENHANCE: Grammar → Verbs**
- ADD concept: "Reflexive verbs (s'appeler, se lever, se coucher)"
- ADD concept: "Verb conjugation for different subjects (je, tu, il/elle, nous, vous, ils/elles)"

**ADD NEW: Vocabulary → Numbers & Technology**
```python
"Numbers & Technology": [
    "Numbers (nombres 0-100)",
    "Digital vocabulary (website=site web, mouse=souris, email=courriel)",
    "Technology terms (ordinateur, clavier, écran)",
    "Question words (comment, qui, quand, où, pourquoi)"
]
```

**ENHANCE: Pronunciation & Reading → Reading Skills**
- ADD concept: "Reading comprehension and image matching"
- ADD concept: "Text comprehension skills"

---

## 3. **GEOGRAPHY** (15 questions analyzed)

### Current Gaps Identified:
- **Administrative divisions** (Grama Niladhari, Divisional Secretariat) - Sri Lankan context missing
- **Directions without compass** (using sun) appears in 4+ questions
- **School location identification** - specific skill tested

### Recommended Changes:

**ADD NEW: Political Geography → Administrative Divisions** (Sri Lankan specific)
```python
"Administrative Divisions": [
    "Grama Niladhari Division (smallest unit)",
    "Divisional Secretariat Division",
    "District",
    "Province",
    "Administrative hierarchy",
    "School location identification system"
]
```

**ADD NEW: Physical Geography → Map Skills & Directions**
```python
"Map Skills & Directions": [
    "Cardinal directions (North, South, East, West)",
    "Finding directions using the sun (sunrise=East, sunset=West)",
    "Finding directions without a compass",
    "Reading maps and plans",
    "School premises mapping",
    "Using symbols on plans"
]
```

---

## 4. **IT** (38 questions analyzed)

### Current Gaps Identified:
- **Robotics** (manufacturing, industry) - 2+ questions, NOT in taxonomy
- **Artificial Intelligence** applications - tested but missing
- **Digital citizenship** and **responsible online behavior** - mentioned but not detailed
- **Algorithms** (sorting) - tested with specific examples
- **Spreadsheet software** and **databases** - tested but not in taxonomy

### Recommended Changes:

**ENHANCE: Internet & Digital World → Internet Basics**
- ADD concept: "Internet Service Providers (ISP)"
- ADD concept: "World Wide Web vs Internet"

**RENAME & ENHANCE: Digital Literacy → Digital Literacy & Safety**
```python
"Digital Literacy & Safety": [
    "Digital citizenship",
    "Responsible online behavior and interactions",
    "Cybersecurity basics",
    "Identifying phishing and suspicious emails",
    "Online privacy protection",
    "Public Wi-Fi safety precautions",
    "Protecting personal data"
]
```

**ADD NEW: Digital Tools & Applications**
```python
"Digital Tools & Applications": {
    "Productivity Software": [
        "Spreadsheet software (Microsoft Excel)",
        "Data analysis and presentation tools",
        "Graphics editors and image editing",
        "Databases and data management"
    ],
    "Computer Graphics": [
        "Pixels and image display",
        "Display technology",
        "Screen resolution"
    ]
}
```

**ENHANCE: Programming Concepts → Basic Concepts**
- ADD concept: "Sorting algorithms (ascending/descending order)"
- ADD concept: "Step-by-step procedures (algorithm for everyday tasks)"

**ADD NEW: Inventions & Innovation → Robotics & Artificial Intelligence**
```python
"Robotics & Artificial Intelligence": [
    "Robots in manufacturing and industry",
    "Industrial robotics applications",
    "Artificial Intelligence basics",
    "AI applications in everyday life",
    "Future of technology and AI"
]
```

---

## 5. **MATHS** (44 questions analyzed)

### Current Gaps Identified:
- **Ratios** appear in 5+ questions (recipes, mixtures, paint) - NOT explicitly in taxonomy
- **Simplifying fractions** - tested but not listed
- **Place value** and **writing numbers in words** - tested
- **Shapes by properties** (e.g., "four right angles, equal sides")

### Recommended Changes:

**ALREADY GOOD:** Number Operations → Number Sense (has place value, writing numbers)
**ALREADY GOOD:** Fractions → has "Simplifying fractions"
**ALREADY GOOD:** Ratios & Proportions subtopic exists

**ENHANCE: Geometry → 2D Shapes**
- ADD concept: "Identifying shapes by properties (angles, side lengths)"
- ADD concept: "Properties of rectangles and squares"

**ENHANCE: Fractions & Decimals → Ratios & Proportions**
- Ensure includes: "Recipe and mixture problems", "Paint mixing ratios"

---

## 6. **SCIENCE** (65 questions analyzed)

### Current Gaps Identified:
- **Pollination** dominates with 20+ questions about:
  - Types of pollination (self vs cross)
  - Pollinators (bees, butterflies, wind, water)
  - Role of pollen
  - Attracting pollinators
  - Importance for food production
  - Ecosystem impact
  - Human activities affecting pollination

### Recommended Changes:

**ADD NEW: Life Science → Plant Life & Reproduction**
```python
"Plant Life & Reproduction": [
    "Plant parts and functions",
    "Photosynthesis basics",
    "Pollination process and purpose",
    "Self-pollination vs cross-pollination",
    "Animal pollinators (bees, butterflies, birds)",
    "Wind and water as pollination agents",
    "Role of pollen in plant reproduction",
    "How flowers attract pollinators (color, scent, nectar)",
    "Pollination and food production",
    "Factors affecting pollination efficiency",
    "Pollination impact on ecosystems and biodiversity",
    "Human activities affecting pollination (deforestation, pesticides)"
]
```

---

## Implementation Priority

### HIGH PRIORITY (Most Frequent Gaps):
1. **Science**: Add Plant Life & Reproduction (20+ questions on this topic)
2. **French**: Add Reflexive Verbs and Numbers & Technology (15+ questions)
3. **IT**: Add Robotics & AI, Digital Literacy & Safety enhancements
4. **Geography**: Add Administrative Divisions and Map Skills & Directions

### MEDIUM PRIORITY:
5. **English**: Add Adjective Order and Adverb Function
6. **Math**: Verify Ratios & Proportions coverage (already added)

### ALREADY IMPLEMENTED:
- ✅ Math: Place Value, Ratios & Proportions, Fraction Simplification

---

## Sample Questions Supporting Each Change

### Science - Pollination (20+ questions):
- "What is the primary purpose of pollination in plants?"
- "Which of the following is a common pollinator of flowers?"
- "What is the difference between self-pollination and cross-pollination?"
- "Why is pollination important for food production?"
- "Can wind be a pollination agent?"
- "How do flowers attract pollinators?"
- "What factors can affect the efficiency of pollination?"
- "How does pollination impact ecosystems?"

### French - Reflexive Verbs (6 questions):
- "How would you introduce yourself in French, using the reflexive verb s'appeler..."
- "What is the correct conjugation of the reflexive verb 's'appeler' for the subject 'nous'?"
- "What is the correct conjugation of the reflexive verb 's'appeler' for the subject 'je'?"

### Geography - Administrative Divisions (8 questions):
- "What is the smallest administrative unit in which a school is located?"
- "What is the order of administrative divisions in Sri Lanka, from smallest to largest?"
- "Explain why knowing the name and number of a Grama Niladhari Division is important..."

### IT - Robotics & AI (3 questions):
- "What is the main purpose of using robots in manufacturing and industry?"
- "Describe some potential applications of artificial intelligence in everyday life"
- "Explain the concept of loops in programming and provide an example..."

---

## Next Steps

1. Apply the HIGH PRIORITY changes to subject_taxonomy.py
2. Regenerate performance report to re-categorize existing questions
3. Verify Neo4j shows specific topics/subtopics/concepts instead of "General"/"Uncategorized"
4. Monitor if AI categorization now properly assigns these topics
