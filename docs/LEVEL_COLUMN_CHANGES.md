# Summary: Adding Level Column to Question Patterns

## Overview

Added a `level` column to the `question_patterns` table to support difficulty-based question generation. This allows the AI service to consider question difficulty when generating practice problems.

## Changes Made

### 1. Database Schema Updates

#### Files Modified:
- `setup_neon_schema.py` - Added `level INTEGER` column to table creation
- `app/db/models.py` - Added `level` field to `QuestionPattern` SQLAlchemy model
- `app/db/neon_provider.py` - Updated queries and initialization to include level column

#### Migration Created:
- `migrations/versions/006_add_level_to_question_patterns.py` - Alembic migration for level column

### 2. API Changes

#### Files Modified:
- `app/api/routes.py` - Updated `/question-patterns` endpoint to return `level` field
- Added new endpoint: `POST /admin/add-level-column` for manual migration

### 3. AI Service Enhancement

#### Files Modified:
- `app/services/ai_service.py` - Modified `generate_practice_questions()` to:
  - Include level information in AI prompt
  - Format patterns as: `{type}: {pattern_text} [Level {level}] (Notes: {notes})`
  - Add AI requirement to consider difficulty levels

### 4. Vercel Migration Support

#### Files Modified:
- `app/db/vercel_migrations.py` - Added level column detection and migration
- Enhanced `init_db()` to handle both notes and level columns
- Updated migration version to 006

## Database Schema Evolution

### Before:
```sql
CREATE TABLE question_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    pattern_text TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### After:
```sql
CREATE TABLE question_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL,
    pattern_text TEXT NOT NULL,
    notes TEXT,
    level INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Usage Examples

### API Response Format:
```json
{
    "id": "uuid",
    "type": "algebra_basic",
    "pattern_text": "a + _ = b",
    "notes": "Find the missing number",
    "level": 2,
    "created_at": "2025-09-01T..."
}
```

### AI Prompt Format:
```
algebra_basic: a + _ = b [Level 2] (Notes: Find the missing number)
```

## Level System Guidelines

Suggested level ranges:
- **Level 1-2**: Basic arithmetic (single digit numbers)
- **Level 3-4**: Intermediate arithmetic (double digit numbers)
- **Level 5-6**: Advanced arithmetic (larger numbers, decimals)
- **Level 7-8**: Pre-algebra concepts
- **Level 9-10**: Advanced algebra and complex operations

## Migration Instructions

### For New Installations:
- Run `python setup_neon_schema.py` - automatically includes level column

### For Existing Installations:
1. **Automatic**: Run `POST /admin/apply-migrations?admin_key=YOUR_KEY`
2. **Manual Alembic**: Run `alembic upgrade head`
3. **Manual SQL**: `ALTER TABLE question_patterns ADD COLUMN level INTEGER;`

### Vercel Deployment:
1. Deploy updated code
2. Call migration endpoint to add level column
3. Verify with status endpoint

## Benefits

1. **Adaptive Difficulty**: AI can generate questions appropriate to student level
2. **Progressive Learning**: Support for difficulty progression
3. **Better Targeting**: Match question complexity to student ability
4. **Enhanced Analytics**: Track performance across difficulty levels
5. **Curriculum Alignment**: Align with educational standards and grade levels

## Backward Compatibility

- Level field is nullable, existing patterns work without modification
- API includes level in responses but handles null values gracefully
- AI service works with patterns both with and without level information
- Migration system detects and adds missing columns automatically
