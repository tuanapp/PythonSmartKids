# User Blocking System

*Last Updated: December 2025*

This document covers the user blocking feature for managing user access.

## Overview

The user blocking system allows administrators to:
- Block users who haven't paid, violated rules, or misused the platform
- Unblock users when issues are resolved
- Track blocking history for audit purposes
- Automatically restrict blocked users from accessing features

---

## API Endpoints

### Block User (Admin)

```http
POST /users/{user_uid}/block
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `reason` | string | Yes | Reason for blocking |
| `blocked_by` | string | Yes | Admin identifier |
| `notes` | string | No | Additional notes |
| `admin_key` | string | Yes | Admin authentication |

**Example**:
```bash
curl -X POST "https://python-smart-kids.vercel.app/users/USER_UID/block" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Subscription expired - please renew",
    "blocked_by": "admin_system",
    "notes": "Auto-blocked due to payment failure",
    "admin_key": "YOUR_ADMIN_KEY"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "User blocked successfully",
  "user_uid": "USER_UID",
  "blocked_at": "2025-12-06T10:30:00+00:00"
}
```

### Unblock User (Admin)

```http
POST /users/{user_uid}/unblock
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `unblocked_by` | string | Yes | Admin identifier |
| `notes` | string | No | Reason for unblocking |
| `admin_key` | string | Yes | Admin authentication |

**Example**:
```bash
curl -X POST "https://python-smart-kids.vercel.app/users/USER_UID/unblock" \
  -H "Content-Type: application/json" \
  -d '{
    "unblocked_by": "admin_name",
    "notes": "Payment received",
    "admin_key": "YOUR_ADMIN_KEY"
  }'
```

### Check User Status (Public)

```http
GET /users/{user_uid}/status
```

**No authentication required** - for client-side blocking checks.

**Example**:
```bash
curl "https://python-smart-kids.vercel.app/users/USER_UID/status"
```

**Response**:
```json
{
  "user_uid": "USER_UID",
  "is_blocked": true,
  "blocked_reason": "Subscription expired - please renew"
}
```

### Get Blocking History (Admin)

```http
GET /users/{user_uid}/blocking-history
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | int | 10 | Number of records |
| `admin_key` | string | - | Admin authentication |

**Example**:
```bash
curl "https://python-smart-kids.vercel.app/users/USER_UID/blocking-history?admin_key=YOUR_KEY&limit=10"
```

**Response**:
```json
[
  {
    "id": 1,
    "user_uid": "USER_UID",
    "action": "BLOCKED",
    "reason": "Subscription expired",
    "blocked_at": "2025-12-06T10:30:00+00:00",
    "blocked_by": "admin_system",
    "unblocked_at": null,
    "notes": "Auto-blocked"
  }
]
```

### Get All Blocked Users (Admin)

```http
GET /admin/blocked-users
```

**Parameters**:
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | int | 100 | Maximum users to return |
| `admin_key` | string | - | Admin authentication |

**Example**:
```bash
curl "https://python-smart-kids.vercel.app/admin/blocked-users?admin_key=YOUR_KEY&limit=100"
```

---

## Database Schema

### Users Table (Blocking Fields)

```sql
-- Added to users table
is_blocked BOOLEAN DEFAULT FALSE NOT NULL,
blocked_reason TEXT,
blocked_at TIMESTAMPTZ,
blocked_by VARCHAR
```

### User Blocking History Table

```sql
CREATE TABLE user_blocking_history (
    id SERIAL PRIMARY KEY,
    user_uid VARCHAR NOT NULL,
    action VARCHAR NOT NULL,          -- 'BLOCKED' or 'UNBLOCKED'
    reason TEXT,
    blocked_at TIMESTAMPTZ,
    blocked_by VARCHAR,
    unblocked_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_user_blocking_history_user_uid ON user_blocking_history(user_uid);
```

---

## Standard Blocking Reasons

Use these messages for consistency:

| Category | Reason Message |
|----------|----------------|
| **Non-Payment** | `Subscription expired - please renew` |
| **Rule Violation** | `Terms of service violation detected` |
| **Abuse** | `Unusual activity detected - account suspended` |
| **Security** | `Security concerns - account under review` |
| **Fraud** | `Fraudulent activity detected` |
| **Temporary** | `Temporary suspension for review` |

---

## How It Works

### Middleware Protection

The `UserBlockingMiddleware` automatically checks every request:

```python
# app/middleware/user_blocking_middleware.py
class UserBlockingMiddleware:
    async def __call__(self, request, call_next):
        uid = extract_uid_from_request(request)
        if uid:
            is_blocked, reason = is_user_blocked(uid)
            if is_blocked:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "User blocked",
                        "reason": reason
                    }
                )
        return await call_next(request)
```

### User Experience Flow

1. **Login**: User authenticates via Firebase
2. **Status Check**: Frontend calls `/users/{uid}/status`
3. **If Blocked**:
   - Show blocking popup with reason
   - Clear local session
   - Redirect to login
4. **API Calls**: Blocked users get 403 Forbidden

### Fail-Open Design

If the blocking check fails (database error, etc.), access is **allowed**:
- Better user experience
- Prevents false lockouts
- Errors are logged for review

---

## Implementation

### Service Layer

```python
# app/services/user_blocking_service.py
class UserBlockingService:
    @staticmethod
    def block_user(db, user_uid, reason, blocked_by, notes=None):
        user = db.query(User).filter(User.uid == user_uid).first()
        user.is_blocked = True
        user.blocked_reason = reason
        user.blocked_at = datetime.now(UTC)
        user.blocked_by = blocked_by
        
        # Record history
        history = UserBlockingHistory(
            user_uid=user_uid,
            action='BLOCKED',
            reason=reason,
            blocked_at=datetime.now(UTC),
            blocked_by=blocked_by,
            notes=notes
        )
        db.add(history)
        db.commit()
        return user
    
    @staticmethod
    def is_user_blocked(db, user_uid):
        user = db.query(User).filter(User.uid == user_uid).first()
        if user and user.is_blocked:
            return True, user.blocked_reason
        return False, None
```

### API Routes

```python
# app/api/routes.py
@router.post("/users/{user_uid}/block")
async def block_user(user_uid: str, reason: str, blocked_by: str, 
                     notes: str = None, admin_key: str = ""):
    # Verify admin
    if admin_key != os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    db = get_session()
    user = UserBlockingService.block_user(db, user_uid, reason, blocked_by, notes)
    db.close()
    
    return {"success": True, "message": "User blocked successfully"}
```

---

## Admin Usage

### Block a User

```python
import requests

response = requests.post(
    f"https://python-smart-kids.vercel.app/users/{user_uid}/block",
    json={
        "reason": "Terms of service violation",
        "blocked_by": "admin_system",
        "notes": "Multiple reports received",
        "admin_key": "YOUR_ADMIN_KEY"
    }
)
print(response.json())
```

### Unblock a User

```python
response = requests.post(
    f"https://python-smart-kids.vercel.app/users/{user_uid}/unblock",
    json={
        "unblocked_by": "admin_name",
        "notes": "Issue resolved",
        "admin_key": "YOUR_ADMIN_KEY"
    }
)
```

### List Blocked Users

```python
response = requests.get(
    "https://python-smart-kids.vercel.app/admin/blocked-users",
    params={"admin_key": "YOUR_ADMIN_KEY", "limit": 100}
)

for user in response.json():
    print(f"{user['email']}: {user['blocked_reason']}")
```

### Review History

```python
response = requests.get(
    f"https://python-smart-kids.vercel.app/users/{user_uid}/blocking-history",
    params={"admin_key": "YOUR_ADMIN_KEY", "limit": 50}
)

for record in response.json():
    print(f"{record['action']} at {record['blocked_at']} by {record['blocked_by']}")
```

---

## Testing

### Manual Testing Flow

1. Create test user
2. Block user via API
3. Try to access as blocked user
4. Verify 403 response
5. Unblock user
6. Verify access restored

### Test Commands

```bash
# Check status
curl "http://localhost:8000/users/test_uid/status"

# Block user
curl -X POST "http://localhost:8000/users/test_uid/block" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test", "blocked_by": "admin", "admin_key": "dev-admin-key"}'

# Verify blocked
curl "http://localhost:8000/users/test_uid/status"

# Unblock
curl -X POST "http://localhost:8000/users/test_uid/unblock" \
  -H "Content-Type: application/json" \
  -d '{"unblocked_by": "admin", "admin_key": "dev-admin-key"}'
```

---

## Troubleshooting

### User Claims Wrong Block

1. Check history: `GET /users/{uid}/blocking-history`
2. Review reason and notes
3. If error, unblock and document

### Blocking Not Working

1. Verify middleware in `app/main.py`
2. Check database schema has blocking fields
3. Test `/users/{uid}/status` endpoint
4. Check application logs

### Database Migration

If blocking fields don't exist:
```bash
curl -X POST "https://python-smart-kids.vercel.app/admin/apply-migrations?admin_key=YOUR_KEY"
```

---

## Best Practices

1. **Clear Reasons**: Always provide understandable block reasons
2. **Document Actions**: Use notes field for context
3. **Regular Reviews**: Periodically check blocked users list
4. **Quick Response**: Handle incorrect blocks promptly
5. **Audit Trail**: Rely on history for accountability

---

## Security

- **Admin key required** for block/unblock operations
- **Public status check** allows clients to verify without admin access
- **All actions logged** in blocking history table
- **Environment variable** for admin key (never hardcode)

---

*For API details, see [API_REFERENCE.md](API_REFERENCE.md)*
*For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md)*
