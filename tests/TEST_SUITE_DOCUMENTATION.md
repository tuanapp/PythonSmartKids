# Test Suite Documentation - Subscription-Based Question Generation

## Overview

This document describes the comprehensive test suite for the subscription-based question generation system. All tests ensure proper handling of free, trial, and premium subscriptions, with correct `is_live` tracking for local vs production calls.

## Test Files

### 1. `test_subscription_limits.py` (NEW - Primary Test Suite)
**Location**: `tests/integration/test_subscription_limits.py`

**Purpose**: Comprehensive integration tests covering all three subscription tiers and their daily limits.

**Test Coverage**:
- **Free Subscription (subscription=0)**:
  - First generation (success)
  - Second generation (success, at limit)
  - Third generation (blocked with 403)
  
- **Trial Subscription (subscription=1)**:
  - First generation (success)
  - Second generation (success, at limit)
  - Third generation (blocked with 403)
  
- **Premium Subscription (subscription=2+)**:
  - Multiple generations (5+) all succeed
  - No daily limit enforced
  - Unlimited access verified

- **is_live Tracking**:
  - Local PC calls have `is_live=False` (test 09)
  - Production app calls have `is_live=True` (test 10)
  
- **Level & Source Tracking**:
  - Difficulty level stored in prompts (test 11)
  - Source (api/cached/fallback) tracked (test 12)

**Key Assertion**: All local PC test calls MUST have `is_live=False`

**Run Command**:
```bash
pytest tests/integration/test_subscription_limits.py -v
```

### 2. `test_prompt_storage_integration.py` (EXISTING - Updated)
**Location**: `tests/integration/test_prompt_storage_integration.py`

**Purpose**: Tests prompt storage functionality with different `is_live` values.

**Test Coverage**:
- Live app calls (`is_live=1`)
- Test/Postman calls (`is_live=0`)
- Default `is_live` behavior (defaults to 1)
- Multiple calls creating multiple records
- Prompt content validation
- Database index verification

**Key Tests**:
- `test_01_prompt_storage_live_call` - Production app call
- `test_02_prompt_storage_test_call` - Local PC test call
- `test_03_prompt_storage_default_is_live` - Default behavior

**Run Command**:
```bash
pytest tests/integration/test_prompt_storage_integration.py -v
```

### 3. `test_api.py` (EXISTING - Updated)
**Location**: `tests/integration/test_api.py`

**Purpose**: Unit tests for API endpoints with mocked dependencies.

**Updates Made**:
- Added `is_live=False` to all test requests (local PC calls)
- Added subscription level mocking (free=0, premium=2)
- Added daily limit checking mocks
- Updated test UIDs to 28 characters (realistic Firebase UID format)

**Key Changes**:
```python
# Before
request_data = {
    "uid": uid,
    "ai_bridge_base_url": None
}

# After
request_data = {
    "uid": uid,
    "level": 1,
    "is_live": False,  # Local PC test call
    "ai_bridge_base_url": None
}
```

**Run Command**:
```bash
pytest tests/integration/test_api.py -v
```

## Subscription Levels Explained

### Free (subscription=0)
- **Daily Limit**: 2 questions/day
- **Behavior**: Blocked after 2 generations with 403 Forbidden
- **Error**: `daily_limit_exceeded`
- **Response Fields**:
  ```json
  {
    "daily_count": 2,
    "daily_limit": 2,
    "is_premium": false
  }
  ```

### Trial (subscription=1)
- **Daily Limit**: 2 questions/day (same as free)
- **Behavior**: Blocked after 2 generations with 403 Forbidden
- **Purpose**: Allow users to test premium features before subscribing
- **Response Fields**: Same as free tier

### Premium (subscription=2+)
- **Daily Limit**: Unlimited
- **Behavior**: Never blocked, can generate infinite questions
- **Response Fields**:
  ```json
  {
    "daily_count": 5,  # Still tracked but no limit
    "daily_limit": null,
    "is_premium": true
  }
  ```

## is_live Flag Behavior

### Local PC Calls (`is_live=False`)
**When**: Running tests from development machine, Postman, curl, etc.

**Setting**:
```python
request_data = {
    "uid": "test-user-123",
    "level": 1,
    "is_live": False  # Explicitly set for local testing
}
```

**Database**: Saved with `is_live=0`

**Purpose**: 
- Distinguish test data from production data
- Allow filtering test calls in analytics
- Debug issues without affecting production metrics

### Production App Calls (`is_live=True`)
**When**: Real users generating questions from the mobile/web app

**Setting**:
```python
request_data = {
    "uid": "user-firebase-uid",
    "level": 3,
    "is_live": True  # Production app call
}
```

**Database**: Saved with `is_live=1`

**Purpose**:
- Track real user interactions
- Calculate accurate metrics
- Monitor production usage

## Running Tests

### All Subscription Tests
```bash
# Run comprehensive subscription limit tests
pytest tests/integration/test_subscription_limits.py -v -s

# Expected: 14 tests, all passing
# ✅ Free user: 3 tests
# ✅ Trial user: 3 tests
# ✅ Premium user: 2 tests
# ✅ is_live tracking: 2 tests
# ✅ Level/source tracking: 2 tests
# ✅ Error handling: 2 tests
```

### All Integration Tests
```bash
# Run all integration tests
pytest tests/integration/ -v

# Skip slow tests
pytest tests/integration/ -v -m "not slow"

# Only Neon database tests
pytest tests/integration/ -v -m neon
```

### Specific Test
```bash
# Run single test method
pytest tests/integration/test_subscription_limits.py::TestSubscriptionBasedQuestionGeneration::test_01_free_user_first_generation_success -v -s
```

### With Coverage
```bash
# Generate coverage report
pytest tests/integration/test_subscription_limits.py --cov=app.services --cov=app.api --cov-report=html
```

## Test Database Setup

Tests use the development database configured in `.env`:
```env
ENVIRONMENT=development
NEON_DBNAME=your_db
NEON_USER=your_user
NEON_PASSWORD=your_password
NEON_HOST=your_host
```

**Important**: Tests create and clean up their own test data using unique UIDs:
- Free: `TestFreeUser123456789012345`
- Trial: `TestTrialUser12345678901234`
- Premium: `TestPremiumUser1234567890123`

## Verification Queries

After running tests, verify data in database:

```sql
-- Check test prompts (should be cleaned up)
SELECT uid, request_type, is_live, level, source, created_at
FROM prompts
WHERE uid LIKE 'Test%User%'
ORDER BY created_at DESC;

-- Should return 0 rows after test cleanup

-- Check today's question counts
SELECT uid, COUNT(*) as count
FROM prompts
WHERE request_type = 'question_generation'
  AND DATE(created_at) = CURRENT_DATE
GROUP BY uid;

-- Verify subscription levels
SELECT uid, email, subscription
FROM users
WHERE uid LIKE 'Test%User%';
```

## Test Assertions Summary

### Daily Limit Tests
| User Type | Test | Expected Result |
|-----------|------|-----------------|
| Free | 1st generation | ✅ 200 OK |
| Free | 2nd generation | ✅ 200 OK |
| Free | 3rd generation | ❌ 403 Forbidden |
| Trial | 1st generation | ✅ 200 OK |
| Trial | 2nd generation | ✅ 200 OK |
| Trial | 3rd generation | ❌ 403 Forbidden |
| Premium | 1st-5th generation | ✅ 200 OK |
| Premium | 6th+ generation | ✅ 200 OK |

### is_live Tests
| Call Type | is_live Setting | Expected DB Value |
|-----------|----------------|-------------------|
| Local PC test | `False` | `0` |
| Production app | `True` | `1` |
| Not specified | (default) | `1` |

### Tracking Tests
| Field | Description | Values |
|-------|-------------|--------|
| `level` | Difficulty 1-6 | `1, 2, 3, 4, 5, 6` |
| `source` | Question origin | `api, cached, fallback` |
| `request_type` | Type of request | `question_generation` |
| `is_live` | Production vs test | `0, 1` |

## Best Practices

### 1. Always Set is_live for Local Tests
```python
# ✅ Good
request = {
    "uid": "test-user",
    "is_live": False  # Explicit for local testing
}

# ❌ Bad (will default to True)
request = {
    "uid": "test-user"
}
```

### 2. Use Realistic Test UIDs
```python
# ✅ Good - 28 characters like Firebase
uid = "TestUser1234567890123456789"

# ❌ Bad - too short
uid = "test"
```

### 3. Clean Up Test Data
```python
@pytest.fixture(scope="class")
def cleanup(db_connection, test_uid):
    # Setup
    yield
    # Cleanup after all tests
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM prompts WHERE uid = %s", (test_uid,))
    db_connection.commit()
```

### 4. Test All Subscription Tiers
Every feature should be tested with:
- Free user (subscription=0)
- Trial user (subscription=1)
- Premium user (subscription=2+)

### 5. Verify Database State
```python
# After API call
assert response.status_code == 200

# Verify in database
prompts = get_prompts_from_db(uid)
assert len(prompts) == 1
assert prompts[0]['is_live'] == 0  # Local test call
```

## Troubleshooting

### Test Failures

**Issue**: Tests fail with 403 when they should pass
```
AssertionError: Expected 200, got 403
```
**Solution**: Check if test user has correct subscription level in database

**Issue**: is_live assertion fails
```
AssertionError: Expected is_live=0, got is_live=1
```
**Solution**: Ensure request includes `is_live=False` for local test calls

**Issue**: Database connection errors
```
psycopg2.OperationalError: could not connect
```
**Solution**: Verify `.env` file has correct Neon database credentials

### Cleanup Issues

**Issue**: Test data not cleaned up
```
AssertionError: Expected 0 prompts, found 3
```
**Solution**: 
1. Run cleanup test: `pytest tests/integration/test_subscription_limits.py::test_99_cleanup -v`
2. Manual cleanup: See "Verification Queries" section above

## Future Enhancements

- [ ] Add tests for subscription upgrade mid-session
- [ ] Test subscription expiration handling
- [ ] Add performance tests for high-volume users
- [ ] Test concurrent requests from same user
- [ ] Add tests for subscription downgrade scenarios

## Related Documentation

- `ARCHITECTURE_SIMPLIFICATION_SUMMARY.md` - Migration 008 details
- `SUBSCRIPTION_TESTING.md` - Manual subscription testing guide
- `Backend_Python/app/services/prompt_service.py` - Daily limit implementation
- `Backend_Python/app/api/routes.py` - API endpoint implementation
