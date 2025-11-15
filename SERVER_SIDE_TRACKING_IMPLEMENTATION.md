# Server-Side Question Generation Tracking - Implementation Summary

## Overview
Successfully implemented comprehensive server-side tracking for question generation limits with full LLM audit trail, replacing client-side localStorage tracking.

## Changes Implemented

### 1. Database Models (`Backend_Python/app/db/models.py`)
**New Models Added:**

#### `QuestionGeneration` Table
Tracks each question generation event:
- `id`: Primary key
- `uid`: User's Firebase UID (foreign key to users)
- `generation_date`: Date only (for daily counting)
- `generation_datetime`: Full timestamp
- `level`: Difficulty level requested (1-6)
- `source`: Origin of questions ('api', 'cached', 'fallback')
- `llm_interaction_id`: Link to LLM interaction (nullable)

#### `LLMInteraction` Table
Tracks all LLM API calls with full details:
- `id`: Primary key
- `uid`: User's Firebase UID (foreign key to users)
- `request_datetime`: When the request was made
- `prompt_text`: Full prompt sent to LLM
- `response_text`: Full response from LLM
- `model_name`: Model used (e.g., 'gpt-4', 'gemini-2.0-flash')
- `prompt_tokens`: Token count for prompt
- `completion_tokens`: Token count for completion
- `total_tokens`: Total tokens used
- `estimated_cost_usd`: Calculated cost in USD
- `response_time_ms`: Response time in milliseconds
- `status`: 'success', 'error', or 'timeout'
- `error_message`: Error details if status != 'success'

**Updated Models:**
- `User` model: Added relationships to `question_generations` and `llm_interactions`

### 2. Database Migration
**File:** `Backend_Python/migrations/versions/2d3eefae954c_add_question_generations_and_llm_.py`

- Created migration to add both new tables with proper foreign keys and indexes
- Applied successfully to database
- Migration handles schema updates without breaking existing data

### 3. QuestionGenerationService (`Backend_Python/app/services/question_generation_service.py`)
**New service for managing question generation limits:**

#### Key Methods:
- `get_daily_generation_count(uid, date)`: Count generations for a specific date
- `can_generate_questions(uid, subscription, max_daily)`: Check if user can generate questions
  - Premium users (subscription >= 2): Unlimited access
  - Free/Trial users (subscription 0-1): Limited to `max_daily_questions` per day (default: 2)
- `record_generation(uid, level, source, llm_interaction_id)`: Log a generation event
- `get_user_generations(uid, start_date, end_date, limit)`: Retrieve generation history

#### Return Format for `can_generate_questions`:
```python
{
    'can_generate': bool,
    'reason': str,
    'current_count': int or None,
    'max_count': int or None,
    'is_premium': bool
}
```

### 4. LLMInteractionService (`Backend_Python/app/services/llm_interaction_service.py`)
**New service for LLM tracking and cost calculation:**

#### Key Methods:
- `calculate_cost(model_name, prompt_tokens, completion_tokens)`: Calculate cost in USD
  - Includes pricing for GPT-4, GPT-3.5, Gemini, and default fallback
- `record_interaction(uid, prompt_text, response_text, model_name, tokens, ...)`: Log LLM call
- `get_user_interactions(uid, limit, status_filter)`: Get interaction history
- `get_user_cost_summary(uid, start_date, end_date)`: Get cost statistics

#### Token Costs (per 1M tokens):
```python
{
    'gpt-4': {'prompt': 30.0, 'completion': 60.0},
    'gpt-4-turbo': {'prompt': 10.0, 'completion': 30.0},
    'gpt-3.5-turbo': {'prompt': 0.5, 'completion': 1.5},
    'gemini-2.0-flash': {'prompt': 0.1, 'completion': 0.4},
    'default': {'prompt': 1.0, 'completion': 2.0}
}
```

### 5. AI Service Updates (`Backend_Python/app/services/ai_service.py`)
**Enhanced `generate_practice_questions()` function:**

#### Changes:
1. Added `uid` parameter (first parameter, required)
2. Integrated `LLMInteractionService` for logging
3. Changed timing from `datetime` to milliseconds (`time.time() * 1000`)
4. Extract token usage from OpenAI response (`completion.usage`)
5. Log LLM interaction in 3 scenarios:
   - Success: After successful validation
   - Validation failure: When AI response fails validation
   - Exception: When API call fails or throws error

#### Logging Points:
```python
# Success case
llm_interaction_id = llm_service.record_interaction(
    uid=uid,
    prompt_text=prompt_text,
    response_text=current_response_text,
    model_name=model_name,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    total_tokens=total_tokens,
    response_time_ms=response_time_ms,
    status='success',
    error_message=None
)
```

### 6. API Endpoint Updates (`Backend_Python/app/api/routes.py`)
**Enhanced `/generate-questions` endpoint:**

#### Flow:
1. **Get User Data**: Fetch user's subscription level from database
2. **Check Limits**: Use `QuestionGenerationService.can_generate_questions()`
   - If limit exceeded: Return HTTP 403 with detailed error
3. **Generate Questions**: Call `generate_practice_questions()` with `uid`
4. **Record Generation**: Log the generation event with source and LLM link
5. **Add Metadata**: Include daily count, limit, and premium status in response

#### New Response Fields:
```python
{
    'questions': [...],  # Existing
    'generation_id': int,  # NEW: Question generation record ID
    'llm_interaction_id': int,  # NEW: LLM interaction record ID
    'source': str,  # NEW: 'api', 'cached', or 'fallback'
    'daily_count': int,  # NEW: Count after this generation
    'daily_limit': int,  # NEW: Max allowed per day
    'is_premium': bool,  # NEW: Premium user status
    # ... existing fields ...
}
```

#### Error Response (403 - Daily Limit Exceeded):
```python
{
    'error': 'daily_limit_exceeded',
    'message': 'Daily limit of 2 questions reached',
    'current_count': 2,
    'max_count': 2,
    'is_premium': False
}
```

### 7. Frontend Updates (NOT YET IMPLEMENTED)
**Still needed in `Frontend_Capacitor/android/app/src/main/assets/public/js/mathQuestions.js`:**

1. Remove `loadDailyQuestionCount()` method
2. Remove `incrementDailyQuestionCount()` method
3. Remove localStorage tracking:
   - `daily_questions_${uid}_${date}` key
4. Update `handleGenerateQuestions()`:
   - Remove `canGenerateQuestions()` check (now server-side)
   - Handle 403 error with detailed message
5. Update `showUpgradePopup()` to use server response data

## Testing Checklist

### Backend Testing:
- [ ] Test new user (subscription 0) with 0 generations - should allow
- [ ] Test free user with 1 generation - should allow (1/2)
- [ ] Test free user with 2 generations - should block (2/2 reached)
- [ ] Test premium user (subscription 2+) with any count - should allow unlimited
- [ ] Test LLM logging on success
- [ ] Test LLM logging on validation failure
- [ ] Test LLM logging on API exception
- [ ] Verify token counts and costs are calculated correctly
- [ ] Check generation records are created with proper source
- [ ] Verify foreign key relationships work correctly

### Frontend Testing (after implementation):
- [ ] Test that limit popup no longer shows incorrectly
- [ ] Verify server-enforced limits are respected
- [ ] Check 403 error handling and user feedback
- [ ] Confirm localStorage is no longer used for limits
- [ ] Test upgrade popup shows correct information from server

## Migration Path

### For Existing Users:
1. Old localStorage data will be ignored (harmless)
2. Server will start fresh count from database
3. First generation will be tracked in database
4. Subsequent generations will be properly limited

### Database Cleanup (Optional):
- Can optionally clear old localStorage keys on first load after update
- No database migration needed for existing users

## Security Improvements
1. **Server-Side Enforcement**: Limits can't be bypassed by clearing localStorage
2. **Audit Trail**: Full LLM interaction history for debugging and cost tracking
3. **Cost Monitoring**: Can track AI costs per user and overall
4. **Rate Limiting**: Proper per-user, per-day rate limiting

## Cost Tracking Benefits
1. **Per-User Costs**: Know exactly how much each user costs
2. **Model Comparison**: Track costs across different AI models
3. **Optimization**: Identify expensive prompts and optimize
4. **Billing**: Can potentially bill premium users based on actual usage

## Next Steps
1. ✅ **Backend Implementation**: COMPLETE
2. ⏳ **Frontend Updates**: Remove client-side tracking and update error handling
3. ⏳ **Testing**: Comprehensive testing of all scenarios
4. ⏳ **Deployment**: Deploy to production with migration
5. ⏳ **Monitoring**: Add alerts for high costs or unusual patterns

## Files Modified

### Created:
- `Backend_Python/app/services/question_generation_service.py`
- `Backend_Python/app/services/llm_interaction_service.py`
- `Backend_Python/migrations/versions/2d3eefae954c_add_question_generations_and_llm_.py`
- `Backend_Python/fix_alembic_version.py` (utility script)

### Modified:
- `Backend_Python/app/db/models.py`
- `Backend_Python/app/services/ai_service.py`
- `Backend_Python/app/api/routes.py`
- `Backend_Python/migrations/env.py`

### Pending Changes:
- `Frontend_Capacitor/android/app/src/main/assets/public/js/mathQuestions.js`

## Architecture Benefits
1. **Centralized Control**: All limits enforced in one place
2. **Scalability**: Easy to add new subscription tiers or adjust limits
3. **Analytics**: Rich data for business intelligence
4. **Debugging**: Complete audit trail for troubleshooting
5. **Compliance**: Full tracking for potential regulatory requirements
