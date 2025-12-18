# SmartBoy API - Sample Curl Requests

This document contains sample curl requests for all backend API endpoints.

**Base URLs:**
- **Local Development:** `http://localhost:8000`
- **Production:** `https://python-smart-kids.vercel.app`

**Replace these placeholders:**
- `{BASE_URL}` - API base URL
- `{ADMIN_KEY}` - Admin key (default: `dev-admin-key`)
- `{USER_UID}` - Firebase User UID (e.g., `FrhUjcQpTDVKK14K4y3thVcPgQd2`)

---

## Table of Contents

1. [User Endpoints](#user-endpoints)
2. [User Blocking Endpoints](#user-blocking-endpoints)
3. [Credits Endpoints](#credits-endpoints)
4. [LLM Models Endpoints](#llm-models-endpoints)
5. [Math Questions Endpoints](#math-questions-endpoints)
6. [Knowledge Game Endpoints](#knowledge-game-endpoints)
7. [Game Scores & Leaderboard](#game-scores--leaderboard)
8. [Admin & Migration Endpoints](#admin--migration-endpoints)
9. [Debug Endpoints](#debug-endpoints)

---

## User Endpoints

### Register User

```bash
curl -X POST "{BASE_URL}/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "FrhUjcQpTDVKK14K4y3thVcPgQd2",
    "email": "student@example.com",
    "name": "John Doe",
    "displayName": "Johnny",
    "gradeLevel": 5,
    "subscription": 0,
    "credits": 10
  }'
```

### Get User Information

```bash
curl -X GET "{BASE_URL}/users/{USER_UID}"
```

**Response includes:** subscription, credits, daily_count, daily_limit, is_premium, is_blocked

### Update User Profile

```bash
curl -X PATCH "{BASE_URL}/users/{USER_UID}/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Updated",
    "displayName": "JohnnyNew",
    "gradeLevel": 6
  }'
```

---

## User Blocking Endpoints

### Block User (Admin)

```bash
curl -X POST "{BASE_URL}/users/{USER_UID}/block?admin_key={ADMIN_KEY}&reason=Violation%20of%20terms&blocked_by=admin@example.com&notes=Multiple%20warnings"
```

### Unblock User (Admin)

```bash
curl -X POST "{BASE_URL}/users/{USER_UID}/unblock?admin_key={ADMIN_KEY}&unblocked_by=admin@example.com&notes=Warning%20issued"
```

### Check User Status (Public)

```bash
curl -X GET "{BASE_URL}/users/{USER_UID}/status"
```

### Get User Blocking History (Admin)

```bash
curl -X GET "{BASE_URL}/users/{USER_UID}/blocking-history?admin_key={ADMIN_KEY}&limit=10"
```

### Get All Blocked Users (Admin)

```bash
curl -X GET "{BASE_URL}/admin/blocked-users?admin_key={ADMIN_KEY}&limit=100"
```

---

## Credits Endpoints

### Adjust User Credits (Admin)

Add credits:
```bash
curl -X POST "{BASE_URL}/admin/users/{USER_UID}/credits?admin_key={ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10,
    "reason": "Manual top-up"
  }'
```

Remove credits:
```bash
curl -X POST "{BASE_URL}/admin/users/{USER_UID}/credits?admin_key={ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": -5,
    "reason": "Refund adjustment"
  }'
```

### Get User Credit Usage

Get today's usage:
```bash
curl -X GET "{BASE_URL}/users/{USER_UID}/credit-usage"
```

Get usage for specific date:
```bash
curl -X GET "{BASE_URL}/users/{USER_UID}/credit-usage?date=2024-12-18"
```

Get usage by game type:
```bash
curl -X GET "{BASE_URL}/users/{USER_UID}/credit-usage?game_type=math"
```

---

## LLM Models Endpoints

### Get Active LLM Models (Public)

All active models:
```bash
curl -X GET "{BASE_URL}/llm-models"
```

Filter by provider:
```bash
curl -X GET "{BASE_URL}/llm-models?provider=google"
```

### Get All LLM Models (Admin)

Including inactive/deprecated:
```bash
curl -X GET "{BASE_URL}/admin/llm-models?admin_key={ADMIN_KEY}&include_inactive=true"
```

### Sync LLM Models from Provider (Admin)

Sync from Google:
```bash
curl -X POST "{BASE_URL}/admin/llm-models/sync?admin_key={ADMIN_KEY}&provider=google"
```

Sync with custom API key:
```bash
curl -X POST "{BASE_URL}/admin/llm-models/sync?admin_key={ADMIN_KEY}&provider=google&api_key=YOUR_GOOGLE_API_KEY"
```

### Update LLM Model (Admin)

Update order and status:
```bash
curl -X PATCH "{BASE_URL}/admin/llm-models/models%2Fgemini-2.0-flash?admin_key={ADMIN_KEY}&order_number=1&active=true&manual=false&display_name=Gemini%202.0%20Flash"
```

**Note:** Model names with `/` must be URL-encoded (e.g., `models/gemini-2.0-flash` → `models%2Fgemini-2.0-flash`)

---

## Math Questions Endpoints

### Submit Math Attempt

```bash
curl -X POST "{BASE_URL}/submit_attempt" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": 1,
    "uid": "{USER_UID}",
    "datetime": "2024-12-18T10:30:00Z",
    "question": "5 + 3 = ?",
    "is_answer_correct": true,
    "correct_answer": "8",
    "qorder": 1
  }'
```

### Analyze Student Performance

```bash
curl -X GET "{BASE_URL}/analyze_student/{USER_UID}"
```

### Generate Math Questions

Basic request:
```bash
curl -X POST "{BASE_URL}/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "is_live": 1
  }'
```

With level filter:
```bash
curl -X POST "{BASE_URL}/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "level": 3,
    "is_live": 1
  }'
```

With custom AI bridge (TensorBlock Forge):
```bash
curl -X POST "{BASE_URL}/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "level": 2,
    "is_live": 1,
    "ai_bridge_base_url": "https://api.tensorblock.co/v1",
    "ai_bridge_api_key": "YOUR_TENSORBLOCK_KEY",
    "ai_bridge_model": "google/gemini-2.0-flash-exp"
  }'
```

### Get Question Patterns

All patterns:
```bash
curl -X GET "{BASE_URL}/question-patterns"
```

Filtered by level:
```bash
curl -X GET "{BASE_URL}/question-patterns?level=3"
```

---

## Knowledge Game Endpoints

### Get All Subjects

All subjects:
```bash
curl -X GET "{BASE_URL}/subjects"
```

Filtered by grade level:
```bash
curl -X GET "{BASE_URL}/subjects?grade_level=5"
```

### Get Single Subject

```bash
curl -X GET "{BASE_URL}/subjects/1"
```

### Get Subject Knowledge Documents

```bash
curl -X GET "{BASE_URL}/subjects/1/knowledge"
```

With filters:
```bash
curl -X GET "{BASE_URL}/subjects/1/knowledge?grade_level=5&level=2"
```

### Generate Knowledge Questions

Basic request:
```bash
curl -X POST "{BASE_URL}/generate-knowledge-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "subject_id": 1,
    "count": 5,
    "is_live": 1
  }'
```

With difficulty level and focus on weak areas:
```bash
curl -X POST "{BASE_URL}/generate-knowledge-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "subject_id": 1,
    "count": 10,
    "level": 3,
    "is_live": 1,
    "focus_weak_areas": true
  }'
```

### Evaluate Knowledge Answers

```bash
curl -X POST "{BASE_URL}/evaluate-answers" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "subject_id": 1,
    "is_live": 1,
    "evaluations": [
      {
        "question": "What is the largest planet in our solar system?",
        "user_answer": "Jupiter",
        "correct_answer": "Jupiter"
      },
      {
        "question": "What is the closest star to Earth?",
        "user_answer": "The Sun",
        "correct_answer": "The Sun"
      }
    ]
  }'
```

### Create Knowledge Document (Admin)

```bash
curl -X POST "{BASE_URL}/admin/knowledge-documents?admin_key={ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": 1,
    "title": "The Water Cycle",
    "content": "The water cycle describes how water evaporates from the surface of the earth, rises into the atmosphere, cools and condenses into rain or snow...",
    "source": "manual-entry",
    "grade_level": 5
  }'
```

### Seed Knowledge Documents (Admin)

```bash
curl -X GET "{BASE_URL}/admin/seed-knowledge-documents?admin_key={ADMIN_KEY}"
```

---

## Game Scores & Leaderboard

### Submit Game Score

Multiplication Time (100 seconds challenge):
```bash
curl -X POST "{BASE_URL}/game-scores" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "user_name": "Johnny",
    "game_type": "multiplication_time",
    "score": 45,
    "time_seconds": 100,
    "total_questions": 50
  }'
```

Multiplication Range (all 88 facts):
```bash
curl -X POST "{BASE_URL}/game-scores" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "{USER_UID}",
    "user_name": "Johnny",
    "game_type": "multiplication_range",
    "score": 88,
    "time_seconds": 180,
    "total_questions": 88
  }'
```

### Get Leaderboard

Top 3 for multiplication_time (highest scores):
```bash
curl -X GET "{BASE_URL}/game-scores/leaderboard/multiplication_time?limit=3"
```

Top 10 for multiplication_range (lowest times):
```bash
curl -X GET "{BASE_URL}/game-scores/leaderboard/multiplication_range?limit=10"
```

### Get User's Scores

All scores:
```bash
curl -X GET "{BASE_URL}/game-scores/user/{USER_UID}"
```

Filtered by game type:
```bash
curl -X GET "{BASE_URL}/game-scores/user/{USER_UID}?game_type=multiplication_time&limit=10"
```

### Get User's Best Scores

```bash
curl -X GET "{BASE_URL}/game-scores/user/{USER_UID}/best?game_type=multiplication_range&limit=3"
```

---

## Admin & Migration Endpoints

### Check Migration Status

```bash
curl -X GET "{BASE_URL}/admin/migration-status?admin_key={ADMIN_KEY}"
```

### Apply Migrations

```bash
curl -X POST "{BASE_URL}/admin/apply-migrations?admin_key={ADMIN_KEY}"
```

---

## Debug Endpoints

### Debug Daily Count

```bash
curl -X GET "{BASE_URL}/debug/daily-count/{USER_UID}"
```

### Debug Subjects Schema

```bash
curl -X GET "{BASE_URL}/debug/subjects-schema"
```

### Debug Knowledge Documents

```bash
curl -X GET "{BASE_URL}/debug/knowledge-documents"
```

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid admin key |
| 403 | Forbidden - Daily limit exceeded or no credits |
| 404 | Not Found - User/resource not found |
| 500 | Internal Server Error |

## Rate Limiting (403 Response)

When a user exceeds their limits, the API returns:

```json
{
  "detail": {
    "error": "no_credits",
    "message": "You have no credits remaining",
    "current_count": 5,
    "max_count": 2,
    "is_premium": false,
    "credits_remaining": 0
  }
}
```

Or for daily limits:

```json
{
  "detail": {
    "error": "daily_limit_exceeded",
    "message": "You have reached your daily question limit",
    "current_count": 2,
    "max_count": 2,
    "is_premium": false,
    "credits_remaining": 5
  }
}
```

---

## PowerShell Examples

For Windows PowerShell, use `Invoke-RestMethod`:

### Register User (PowerShell)

```powershell
$body = @{
    uid = "FrhUjcQpTDVKK14K4y3thVcPgQd2"
    email = "student@example.com"
    name = "John Doe"
    displayName = "Johnny"
    gradeLevel = 5
    subscription = 0
    credits = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/users/register" -Method POST -Body $body -ContentType "application/json"
```

### Generate Questions (PowerShell)

```powershell
$body = @{
    uid = "FrhUjcQpTDVKK14K4y3thVcPgQd2"
    level = 3
    is_live = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/generate-questions" -Method POST -Body $body -ContentType "application/json"
```

### Sync LLM Models (PowerShell)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/admin/llm-models/sync?admin_key=dev-admin-key&provider=google" -Method POST
```
