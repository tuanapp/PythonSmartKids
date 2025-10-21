# Prompt Storage Implementation Summary

## Overview
This implementation adds the ability to store AI prompts (both request and response) in a new `prompts` table when questions are generated via the `/generate-questions` endpoint.

## Changes Made

### 1. Database Model (`app/models/schemas.py`)
- ✅ Added `is_live` field to `GenerateQuestionsRequest` schema
  - Type: `Optional[int]`
  - Default: `1` (live from app)
  - Values: `1` = live from application, `0` = test call (Postman, etc.)

### 2. Database Models (`app/db/models.py`)
- ✅ Added new `Prompt` SQLAlchemy model
  - Fields:
    - `id` (Integer, Primary Key)
    - `uid` (String, Firebase User UID)
    - `request_text` (Text, AI prompt request)
    - `response_text` (Text, AI response)
    - `is_live` (Integer, default=1)
    - `created_at` (DateTime with timezone)

### 3. Database Interface (`app/db/db_interface.py`)
- ✅ Added `save_prompt()` abstract method to `DatabaseProvider` interface
  - Parameters: `uid`, `request_text`, `response_text`, `is_live=1`

### 4. Database Provider (`app/db/neon_provider.py`)
- ✅ Added `prompts` table creation in `init_db()` method
  - Includes indexes on `uid` and `created_at` for performance
- ✅ Implemented `save_prompt()` method
  - Inserts prompt data into database
  - Uses NOW() for timestamp
  - Proper error handling and logging

### 5. Database Service (`app/repositories/db_service.py`)
- ✅ Added `save_prompt()` wrapper function
  - Calls provider's `save_prompt()` method
  - Consistent with other service methods

### 6. AI Service (`app/services/ai_service.py`)
- ✅ Modified `generate_practice_questions()` return value
  - Added `ai_request` field containing the prompt text
  - Included in both successful and fallback responses
  - Extracts from `prompt['content']`

### 7. API Routes (`app/api/routes.py`)
- ✅ Modified `/generate-questions` endpoint
  - Accepts `is_live` parameter from request
  - Extracts `ai_request` and `ai_response` from AI service response
  - Calls `db_service.save_prompt()` after successful generation
  - Non-blocking: prompt save failure doesn't fail the request
  - Added detailed logging

## Database Schema

```sql
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    uid TEXT NOT NULL,
    request_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    is_live INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompts_uid ON prompts(uid);
CREATE INDEX idx_prompts_created_at ON prompts(created_at);
```

## Usage

### From Application (Live)
```json
POST /generate-questions
{
    "uid": "FrhUjcQpTDVKK14K4y3thVcPgQd2",
    "level": 3,
    "is_live": 1
}
```

### From Postman/Testing (Non-Live)
```json
POST /generate-questions
{
    "uid": "test_user_123",
    "level": 2,
    "is_live": 0
}
```

### Default Behavior
If `is_live` is not specified, it defaults to `1` (live).

## Benefits

1. **Analytics**: Track what prompts are being sent to AI
2. **Debugging**: Review exact prompts and responses for troubleshooting
3. **Audit Trail**: Know when and how questions were generated
4. **Testing Distinction**: Separate live app usage from test API calls
5. **Performance Monitoring**: Analyze prompt patterns and response quality

## Files Modified

1. `Backend_Python/app/models/schemas.py` - Added `is_live` field
2. `Backend_Python/app/db/models.py` - Added `Prompt` model
3. `Backend_Python/app/db/db_interface.py` - Added `save_prompt()` abstract method
4. `Backend_Python/app/db/neon_provider.py` - Implemented table creation and save method
5. `Backend_Python/app/repositories/db_service.py` - Added service wrapper
6. `Backend_Python/app/services/ai_service.py` - Added `ai_request` to return value
7. `Backend_Python/app/api/routes.py` - Integrated prompt saving into endpoint

## Testing

To test the implementation:

1. **Start the backend server**
   ```powershell
   cd Backend_Python
   .\start-dev.ps1
   ```

2. **Test with Postman (non-live)**
   ```bash
   POST http://localhost:8000/generate-questions
   {
       "uid": "test_user_xyz",
       "level": 1,
       "is_live": 0
   }
   ```

3. **Test from app (live)**
   - Use the math questions page in the app
   - The `is_live` field will automatically be `1`

4. **Verify in database**
   ```sql
   SELECT * FROM prompts ORDER BY created_at DESC LIMIT 10;
   ```

## Migration

The `prompts` table will be automatically created when:
- The application starts and `init_db()` is called
- The Neon provider's `init_db()` method runs

No manual migration is required for existing installations.

## Notes

- Prompt saving is non-blocking: if it fails, the question generation still succeeds
- All errors are logged for debugging
- Indexes are created for efficient querying by user and date
- The table uses PostgreSQL TIMESTAMPTZ for proper timezone handling
