# Level-Based Pattern Filtering

## Overview

Added level-based filtering to the question patterns system. Now the API can filter patterns by difficulty level when generating questions or retrieving patterns.

## API Changes

### 1. Generate Questions Endpoint

**Endpoint**: `POST /generate-questions`

**Updated Request Body**:
```json
{
    "uid": "student_user_id",
    "level": 3,  // Optional: Filter patterns by this level
    "ai_bridge_base_url": "optional_url",
    "ai_bridge_api_key": "optional_key", 
    "ai_bridge_model": "optional_model"
}
```

**Behavior**:
- If `level` is provided: Returns patterns with matching level OR null level
- If `level` is omitted: Returns all patterns
- Patterns are ordered by level (ascending)

### 2. Question Patterns Endpoint

**Endpoint**: `GET /question-patterns?level=3`

**Parameters**:
- `level` (optional): Integer to filter patterns by difficulty level

**Examples**:
```bash
# Get all patterns
GET /question-patterns

# Get patterns for level 3 (includes level 3 and null level patterns)
GET /question-patterns?level=3
```

## Database Changes

### New Method: `get_question_patterns_by_level(level)`

**SQL Query Logic**:
```sql
-- When level is specified
SELECT id, type, pattern_text, notes, level, created_at
FROM question_patterns
WHERE level = %s OR level IS NULL
ORDER BY level ASC;

-- When level is None
SELECT id, type, pattern_text, notes, level, created_at
FROM question_patterns
ORDER BY level ASC;
```

**Rationale**: Including `NULL` level patterns allows patterns without assigned levels to be available at all difficulty levels.

## Implementation Details

### Database Layer
- `app/db/db_interface.py`: Added abstract method `get_question_patterns_by_level()`
- `app/db/neon_provider.py`: Implemented level filtering with NULL handling
- `app/repositories/db_service.py`: Added service method wrapper

### API Layer
- `app/models/schemas.py`: Added optional `level` field to `GenerateQuestionsRequest`
- `app/api/routes.py`: Updated both endpoints to support level filtering

### AI Service Layer
- No changes needed - continues to use whatever patterns are provided
- Level information still appears in AI prompts when available

## Usage Examples

### Frontend Integration

```javascript
// Generate questions for level 3 difficulty
const response = await fetch('/generate-questions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        uid: 'student_123',
        level: 3
    })
});

// Get all patterns for level 5
const patterns = await fetch('/question-patterns?level=5');
```

### Python/Testing

```python
# Generate questions with level filtering
request_data = {
    "uid": "test_student",
    "level": 2
}
response = requests.post("/generate-questions", json=request_data)

# Get patterns for specific level
patterns = requests.get("/question-patterns?level=4")
```

## Level Guidelines

Recommended level structure:
- **Level 1**: Basic single-digit arithmetic
- **Level 2**: Double-digit basic operations
- **Level 3**: Multi-digit arithmetic, simple fractions
- **Level 4**: Decimals, percentages, complex fractions
- **Level 5**: Pre-algebra, equations with variables
- **Level 6+**: Advanced algebra and beyond

## Backward Compatibility

- Existing API calls without `level` parameter continue to work unchanged
- Patterns with `NULL` level are included in all level queries
- All existing functionality remains intact
- AI service generates questions using provided patterns regardless of how they were filtered

## Benefits

1. **Adaptive Difficulty**: Generate questions appropriate to student skill level
2. **Progressive Learning**: Support structured learning paths
3. **Curriculum Alignment**: Match educational standards and grade levels
4. **Better Targeting**: Focus practice on appropriate difficulty
5. **Flexible Filtering**: Include general patterns (NULL level) with specific levels
