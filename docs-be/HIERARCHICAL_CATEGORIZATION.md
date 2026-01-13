# Hierarchical Question Categorization System

## Overview

SmartBoy now uses a comprehensive hierarchical categorization system for all questions across all subjects. This enables granular performance tracking and targeted learning recommendations.

## Architecture

### Hierarchical Levels

```
Subject
  ↓
Topic
  ↓
SubTopic
  ↓
Concept (Atomic Skill)
  ↓
Question
  ↓
KnowledgeAttempt (Student's Answer)
```

### Example: Math Question

```
Subject: Math
  Topic: Fractions & Decimals
    SubTopic: Fractions
      Concept: Dividing fractions
        Question: "What is 3/4 ÷ 1/2?"
          KnowledgeAttempt: Student answered "3/8" (incorrect, correct is "3/2")
```

## Subject Taxonomy

### Supported Subjects

1. **Math**
   - Topics: Number Operations, Fractions & Decimals, Geometry, Algebra, Measurement, Data & Statistics, Word Problems
   
2. **English**
   - Topics: Grammar, Vocabulary, Reading Comprehension, Writing, Phonics & Spelling
   
3. **Science**
   - Topics: Life Science, Physical Science, Earth & Space Science, Scientific Inquiry
   
4. **General Knowledge**
   - Topics: Geography, History, Current Affairs
   
5. **IT**
   - Topics: Computer Basics, Internet & Digital Literacy, Programming Concepts

### Complete Taxonomy

See [`subject_taxonomy.py`](../app/services/subject_taxonomy.py) for the complete hierarchical structure of all subjects.

## Neo4j Graph Structure

### Nodes

- **Subject**: Top-level subject (Math, English, Science, etc.)
- **Topic**: Major area within a subject
- **SubTopic**: Specific area within a topic
- **Concept**: Atomic skill or concept
- **Question**: The question being asked
- **KnowledgeAttempt**: Student's answer to a question
- **Student**: The student

### Relationships

```cypher
(:Subject)-[:HAS_TOPIC]->(:Topic)
(:Topic)-[:HAS_SUBTOPIC]->(:SubTopic)
(:SubTopic)-[:HAS_CONCEPT]->(:Concept)
(:Concept)-[:HAS_QUESTION]->(:Question)
(:Question)<-[:ANSWERED]-(:KnowledgeAttempt)
(:Student)-[:ATTEMPTED]->(:KnowledgeAttempt)
(:KnowledgeAttempt)-[:BELONGS_TO]->(:Subject)

// Cross-references for efficient querying
(:Question)-[:TESTS_CONCEPT]->(:Concept)
(:Question)-[:TESTS_SUBTOPIC]->(:SubTopic)
(:Question)-[:TESTS_TOPIC]->(:Topic)
```

## Question Properties

### Enhanced Metadata

Each question now includes:

```json
{
  "id": "unique_id",
  "text": "Question text",
  "difficulty": 3,           // 1-5 scale
  "bloomsLevel": "apply",    // remember, understand, apply, analyze, evaluate, create
  "subjectId": "subject_id"
}
```

### KnowledgeAttempt Properties

```json
{
  "id": "attempt_id",
  "question": "Question text",
  "isCorrect": false,
  "userAnswer": "Student's answer",
  "correctAnswer": "Correct answer",
  "topic": "Fractions & Decimals",
  "subtopic": "Fractions",
  "concept": "Dividing fractions",
  "difficulty": 3,
  "bloomsLevel": "apply",
  "embedding": [0.1, 0.2, ...],  // Vector embedding
  "embeddingText": "Full context for embedding"
}
```

## AI Categorization Process

### How It Works

1. **Batch Processing**: Questions are grouped by subject for efficient categorization
2. **AI Analysis**: Gemini AI analyzes each question and assigns:
   - Topic (from predefined taxonomy)
   - SubTopic (from predefined taxonomy)
   - Concept (specific atomic skill)
   - Difficulty (1-5)
   - Bloom's Level (cognitive complexity)
3. **Graph Creation**: Hierarchical structure is created in Neo4j
4. **Caching**: Categorization is cached on KnowledgeAttempt for fast retrieval

### Example AI Categorization

Input:
```
Question: "What is 3/4 ÷ 1/2?"
Subject: Math
```

Output:
```json
{
  "topic": "Fractions & Decimals",
  "subtopic": "Fractions",
  "concept": "Dividing fractions",
  "difficulty": 3,
  "blooms_level": "apply"
}
```

## Retrieval Queries

### 1. Hierarchical Graph Context

Retrieves performance data organized by Topic → SubTopic → Concept:

```cypher
MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
  AND ($topic IS NULL OR toLower(ka.topic) CONTAINS toLower($topic))
WITH sub.name AS subject, ka.topic AS topic, ka.subtopic AS subtopic, ka.concept AS concept,
     ka.difficulty AS difficulty, ka.bloomsLevel AS bloomsLevel,
     count(CASE WHEN ka.isCorrect = false THEN 1 END) AS incorrect_count,
     count(CASE WHEN ka.isCorrect = true THEN 1 END) AS correct_count
RETURN subject, topic, subtopic, concept, difficulty, bloomsLevel,
       correct_count, incorrect_count, total, accuracy
ORDER BY subject, incorrect DESC, total DESC
```

### 2. Hierarchical Concept Breakdown

Provides detailed breakdown by Topic/SubTopic/Concept with difficulty and Bloom's level:

```cypher
MATCH (s:Student {uid: $uid})-[:ATTEMPTED]->(ka:KnowledgeAttempt)-[:BELONGS_TO]->(sub:Subject)
WHERE ($subject IS NULL OR toLower(sub.name) = toLower($subject))
  AND ($topic IS NULL OR toLower(ka.topic) CONTAINS toLower($topic))
  AND ka.topic IS NOT NULL
RETURN subject, topic, subtopic, concept, difficulty, bloomsLevel,
       correct_count, incorrect_count, total, accuracy
ORDER BY subject, topic, incorrect DESC, total DESC
```

### 3. Vector Similarity with Hierarchy

Finds similar questions and includes their hierarchical categorization:

```cypher
CALL db.index.vector.queryNodes('attempt_embeddings', 10, $query_embedding)
YIELD node, score
MATCH (node)-[:BELONGS_TO]->(sub:Subject)
WHERE node.uid = $uid
  AND ($subject IS NULL OR toLower(sub.name) = toLower($subject))
  AND ($topic IS NULL OR toLower(node.topic) CONTAINS toLower($topic))
RETURN node.question, node.topic, node.subtopic, node.concept,
       node.difficulty, node.bloomsLevel, sub.name AS subject, score
ORDER BY score DESC
```

## Query Results Format

### Hierarchical Performance Breakdown

```
📚 Math:
  📖 Fractions & Decimals:
    • Fractions → Dividing fractions: 5/8 wrong (37.5% accuracy) [Difficulty: ⭐⭐⭐, Bloom's: apply]
    • Decimals → Adding decimals: 2/10 wrong (80% accuracy) [Difficulty: ⭐⭐, Bloom's: understand]
  📖 Geometry:
    • 2D Shapes → Area calculations: 3/6 wrong (50% accuracy) [Difficulty: ⭐⭐⭐⭐, Bloom's: apply]
```

### Vector Context with Hierarchy

```
- **Math** → Fractions & Decimals → Fractions → Dividing fractions
  Q: What is 3/4 ÷ 1/2?
  Student: 3/8 | Correct: 3/2 | Difficulty: ⭐⭐⭐ | Bloom's: apply | Similarity: 0.923
```

## Benefits

### For Students

1. **Targeted Practice**: Know exactly which concepts need work
2. **Difficulty Progression**: Understand which difficulty levels are challenging
3. **Cognitive Level Awareness**: See if struggles are in basic recall vs higher-order thinking

### For AI Analysis

1. **Precise Recommendations**: "Practice dividing fractions" vs "improve Math"
2. **Difficulty-Aware Suggestions**: Recommend appropriate difficulty progression
3. **Bloom's-Based Strategies**: Tailor study methods to cognitive level

### For Teachers/Parents

1. **Granular Insights**: See specific weak concepts, not just subjects
2. **Pattern Recognition**: Identify if student struggles with certain difficulty levels or cognitive tasks
3. **Progress Tracking**: Monitor improvement at concept level

## Example Queries

### "What types of questions did I get wrong most often in Math?"

AI will analyze:
- Topics with most errors
- SubTopics with most errors
- Specific Concepts with most errors
- Difficulty distribution of errors
- Bloom's level distribution

Response:
```
In Math, you struggled most with:

📖 Fractions & Decimals (60% of errors)
  • Fractions → Dividing fractions: 5/8 wrong (⭐⭐⭐ difficulty, apply level)
  • Fractions → Multiplying fractions: 3/7 wrong (⭐⭐ difficulty, apply level)

📖 Geometry (30% of errors)
  • 2D Shapes → Area calculations: 3/6 wrong (⭐⭐⭐⭐ difficulty, apply level)

Pattern: You're struggling with application-level problems (Bloom's: apply) 
at medium-high difficulty (⭐⭐⭐-⭐⭐⭐⭐). These require using learned concepts 
in new situations.

Recommendation: Focus on practicing dividing fractions with guided examples 
before attempting independent problems.
```

## Implementation Details

### Data Ingestion

When questions are imported:

1. Questions grouped by subject
2. Batch sent to AI for hierarchical categorization
3. Neo4j graph structure created:
   - Subject → Topic → SubTopic → Concept → Question → KnowledgeAttempt
4. Hierarchical metadata cached on KnowledgeAttempt for fast retrieval
5. Vector embeddings generated and stored

### Retrieval Process

When generating reports or answering queries:

1. **Graph Context**: Retrieve hierarchical performance breakdown
2. **Concept Breakdown**: Get detailed Topic/SubTopic/Concept analysis
3. **Vector Context**: Find similar questions with hierarchical metadata
4. **Combine**: Merge all contexts with hierarchical structure
5. **Analyze**: AI generates insights using hierarchical data

### Skip Data Ingestion Mode

For performance, Q&A queries now skip data re-ingestion:
- Connect to Neo4j but don't re-import
- Use existing hierarchical structure
- Fast retrieval with filters

## Future Enhancements

### Potential Additions

1. **Grade Level Linking**
   ```cypher
   (:Question)-[:SUITABLE_FOR]->(:Grade {value: 6})
   ```

2. **Syllabus Alignment**
   ```cypher
   (:Concept)-[:ALIGNS_WITH]->(:SyllabusOutcome {code: "G6.MATH.FRAC.3"})
   ```

3. **Question Sets**
   ```cypher
   (:QuestionSet {name: "Fractions Mastery"})-[:CONTAINS]->(:Question)
   ```

4. **Learning Paths**
   ```cypher
   (:Concept)-[:PREREQUISITE_FOR]->(:Concept)
   ```

5. **Mastery Tracking**
   - Track mastery percentage per concept
   - Suggest progression when concepts mastered

## Testing

To test the hierarchical categorization:

1. **Generate a report** (triggers full data ingestion with categorization)
2. **Ask specific queries** like:
   - "What types of questions did I get wrong in Math?"
   - "Show me my weak areas in English Grammar"
   - "Which concepts do I struggle with most?"

The AI will now provide granular, hierarchical insights!

## Maintenance

### Adding New Subjects

1. Update [`subject_taxonomy.py`](../app/services/subject_taxonomy.py)
2. Add subject with Topic → SubTopic → Concept structure
3. AI will automatically use new taxonomy

### Modifying Taxonomy

1. Edit taxonomy in `subject_taxonomy.py`
2. Re-run data ingestion to re-categorize questions
3. Existing data will be updated with new categories

## Performance Considerations

- **Batch Categorization**: ~10-20 questions per AI call
- **Caching**: Categories stored on KnowledgeAttempt nodes
- **Skip Ingestion**: Q&A queries skip re-categorization
- **Indexed Queries**: Neo4j indexes on topic, subtopic, concept for fast filtering
