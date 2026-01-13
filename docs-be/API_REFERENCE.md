# API Reference

*Last Updated: December 2025*

Complete reference for all SmartBoy backend API endpoints.

## Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://python-smart-kids.vercel.app` |
| Development | `http://localhost:8000` |

## Interactive Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

---

## Core Endpoints

### Generate Questions

Generate AI-powered practice questions for a student.

```http
POST /generate-questions
```

**Request Body**:
```json
{
  "uid": "firebase-user-uid",
  "level": 3,
  "is_live": 1,
  "ai_bridge_base_url": "optional-override",
  "ai_bridge_api_key": "optional-override",
  "ai_bridge_model": "optional-override"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uid` | string | Yes | Firebase user UID |
| `level` | int | No | Difficulty level (1-6) |
| `is_live` | int | No | 1=app, 0=test (default: 1) |
| `ai_bridge_*` | string | No | Override AI settings |

**Response** (Success):
```json
{
  "questions": [...],
  "prompt_id": 123,
  "daily_count": 1,
  "daily_limit": 2,
  "is_premium": false,
  "model_info": {
    "model_name": "gemini-2.0-flash",
    "response_time_ms": 1234,
    "total_tokens": 500
  }
}
```

**Response** (Limit Exceeded):
```json
{
  "detail": "Daily limit reached (2/2). Upgrade to premium for unlimited access."
}
```
Status: `403 Forbidden`

---

### Submit Attempt

Record a student's answer to a math question.

```http
POST /submit_attempt
```

**Request Body**:
```json
{
  "student_id": 123,
  "uid": "firebase-user-uid",
  "datetime": "2025-12-06T10:30:00",
  "question": "What is 2 + 3?",
  "is_answer_correct": true,
  "incorrect_answer": null,
  "correct_answer": "5",
  "qorder": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `student_id` | int | Yes | Student identifier |
| `uid` | string | Yes | Firebase user UID |
| `datetime` | datetime | Yes | When answered |
| `question` | string | Yes | The question text |
| `is_answer_correct` | bool | Yes | Was answer correct |
| `incorrect_answer` | string | No | What user answered (if wrong) |
| `correct_answer` | string | Yes | Correct answer |
| `qorder` | int | No | Question order in session |

**Response**:
```json
{
  "message": "What is 2 + 3? Attempt saved successfully - 2025-12-06 10:30:00"
}
```

---

### Analyze Student

Get AI-powered analysis of student performance.

```http
GET /analyze_student/{uid}
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `uid` | string | Firebase user UID |

**Response**:
```json
{
  "analysis": "Student shows strength in addition...",
  "weak_areas": ["multiplication", "fractions"],
  "recommendations": [...]
}
```

---

### Get Question Patterns

Retrieve question patterns for question generation.

```http
GET /question-patterns
```

**Query Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `level` | int | - | Filter by difficulty level |

**Response**:
```json
[
  {
    "id": "uuid-here",
    "type": "algebra",
    "pattern_text": "a + b = _",
    "notes": "Simple addition",
    "level": 1,
    "created_at": "2025-12-06T10:00:00+00:00"
  }
]
```

---

## User Endpoints

### Register User

Register a new user in the backend database.

```http
POST /users/register
```

**Request Body**:
```json
{
  "uid": "firebase-uid",
  "email": "user@example.com",
  "name": "John Doe",
  "displayName": "John",
  "gradeLevel": 5,
  "registrationDate": "2025-12-06T10:00:00"
}
```

**Response**:
```json
{
  "message": "User registered successfully",
  "uid": "firebase-uid",
  "email": "user@example.com",
  "name": "John Doe",
  "registrationDate": "2025-12-06T10:00:00"
}
```

---

### Get User

Get user information including subscription and daily usage.

```http
GET /users/{uid}
```

**Response**:
```json
{
  "uid": "firebase-uid",
  "email": "user@example.com",
  "name": "John Doe",
  "displayName": "John",
  "gradeLevel": 5,
  "subscription": 0,
  "registrationDate": "2025-12-06T10:00:00",
  "daily_count": 1,
  "daily_limit": 2,
  "is_premium": false
}
```

---

### Check User Status

Check if user is blocked.

```http
GET /users/{user_uid}/status
```

**Response**:
```json
{
  "user_uid": "firebase-uid",
  "is_blocked": false,
  "blocked_reason": null
}
```

---

## Admin Endpoints

All admin endpoints require `admin_key` parameter.

### Migration Status

Check database migration status.

```http
GET /admin/migration-status?admin_key=YOUR_KEY
```

**Response**:
```json
{
  "current_version": "008",
  "alembic_table_exists": true,
  "existing_tables": ["attempts", "question_patterns", "users", "prompts"],
  "notes_column_exists": true,
  "level_column_exists": true,
  "prompts_table_exists": true,
  "prompts_indexes_exist": true,
  "user_blocking_exists": true,
  "user_blocking_history_exists": true,
  "needs_migration": false
}
```

---

### Apply Migrations

Apply all pending database migrations.

```http
POST /admin/apply-migrations?admin_key=YOUR_KEY
```

**Response**:
```json
{
  "success": true,
  "message": "All migrations applied successfully",
  "final_status": {...}
}
```

---

### Block User

Block a user from accessing the application.

```http
POST /users/{user_uid}/block
```

**Parameters**:
```json
{
  "reason": "Subscription expired",
  "blocked_by": "admin_name",
  "notes": "Optional notes",
  "admin_key": "YOUR_KEY"
}
```

**Response**:
```json
{
  "success": true,
  "message": "User blocked successfully",
  "user_uid": "firebase-uid",
  "blocked_at": "2025-12-06T10:30:00+00:00"
}
```

---

### Unblock User

Unblock a previously blocked user.

```http
POST /users/{user_uid}/unblock
```

**Parameters**:
```json
{
  "unblocked_by": "admin_name",
  "notes": "Issue resolved",
  "admin_key": "YOUR_KEY"
}
```

---

### Get Blocking History

Get blocking history for a user.

```http
GET /users/{user_uid}/blocking-history?admin_key=YOUR_KEY&limit=10
```

**Response**:
```json
[
  {
    "id": 1,
    "user_uid": "firebase-uid",
    "action": "BLOCKED",
    "reason": "Subscription expired",
    "blocked_at": "2025-12-06T10:30:00+00:00",
    "blocked_by": "admin_system",
    "unblocked_at": null,
    "notes": null
  }
]
```

---

### Get Blocked Users

Get all currently blocked users.

```http
GET /admin/blocked-users?admin_key=YOUR_KEY&limit=100
```

**Response**:
```json
[
  {
    "uid": "firebase-uid",
    "email": "user@example.com",
    "name": "John Doe",
    "is_blocked": true,
    "blocked_reason": "Subscription expired",
    "blocked_at": "2025-12-06T10:30:00+00:00",
    "blocked_by": "admin_system"
  }
]
```

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | Request completed |
| `400` | Bad Request | Invalid parameters |
| `401` | Unauthorized | Invalid admin key |
| `403` | Forbidden | User blocked or limit exceeded |
| `404` | Not Found | User or resource not found |
| `500` | Server Error | Internal error |

---

## Rate Limits

| User Type | Limit |
|-----------|-------|
| Free (subscription=0) | 2 generations/day |
| Trial (subscription=1) | 2 generations/day |
| Premium (subscription≥2) | Unlimited |

---

## Authentication

- **Firebase Auth**: Frontend handles authentication
- **Admin Key**: Required for admin endpoints via `admin_key` parameter
- **User UID**: Passed in request body or URL path

---

*For testing endpoints, use Swagger UI at `/docs`*
