# User Blocking System Documentation

## Overview
The SmartBoy application now includes a comprehensive user blocking system that allows administrators to block users who haven't paid, violated rules, or misused the platform.

## Architecture

### Backend Components

#### 1. Database Schema
**Location**: `Backend_Python/migrations/add_user_blocking.sql`

**Users Table** - Added blocking fields:
- `is_blocked` (BOOLEAN) - Whether user is currently blocked
- `blocked_reason` (TEXT) - Reason for blocking
- `blocked_at` (TIMESTAMP) - When user was blocked
- `blocked_by` (VARCHAR) - Admin identifier who blocked the user

**User Blocking History Table** - Tracks all blocking actions:
- `id` (SERIAL PRIMARY KEY)
- `user_uid` (VARCHAR) - User's Firebase UID
- `action` (VARCHAR) - 'BLOCKED' or 'UNBLOCKED'
- `reason` (TEXT) - Reason for action
- `blocked_at` (TIMESTAMP) - When action was taken
- `blocked_by` (VARCHAR) - Admin identifier
- `unblocked_at` (TIMESTAMP) - When user was unblocked
- `notes` (TEXT) - Additional notes

#### 2. Models
**Location**: `Backend_Python/app/db/models.py`

- `User` - SQLAlchemy model with blocking fields
- `UserBlockingHistory` - SQLAlchemy model for blocking history

#### 3. Service Layer
**Location**: `Backend_Python/app/services/user_blocking_service.py`

**UserBlockingService** provides:
- `block_user()` - Block a user with reason
- `unblock_user()` - Unblock a user
- `is_user_blocked()` - Check if user is blocked
- `get_blocking_history()` - Get user's blocking history
- `get_all_blocked_users()` - Get all currently blocked users

#### 4. API Endpoints
**Location**: `Backend_Python/app/api/routes.py`

- `POST /users/{user_uid}/block` - Block a user (requires admin key)
- `POST /users/{user_uid}/unblock` - Unblock a user (requires admin key)
- `GET /users/{user_uid}/status` - Check if user is blocked (public)
- `GET /users/{user_uid}/blocking-history` - Get blocking history (requires admin key)
- `GET /admin/blocked-users` - Get all blocked users (requires admin key)

#### 5. Middleware
**Location**: `Backend_Python/app/middleware/user_blocking_middleware.py`

**UserBlockingMiddleware** automatically checks blocking status on all requests and returns 403 Forbidden if user is blocked.

### Frontend Components

#### 1. API Helper
**Location**: `Frontend_Capacitor/android/app/src/main/assets/public/js/apiHelper.js`

Added `checkUserStatus()` method to check if user is blocked.

#### 2. Math Questions Manager
**Location**: `Frontend_Capacitor/android/app/src/main/assets/public/js/mathQuestions.js`

Added methods:
- `checkUserBlockingStatus()` - Check if user is blocked
- `handleBlockedUser()` - Clear session and show popup
- `showBlockingPopup()` - Display blocking message to user

## Usage

### Deploying the Database Changes

1. **Run the migration SQL script**:
```bash
cd Backend_Python
psql -h YOUR_NEON_HOST -U YOUR_USER -d YOUR_DATABASE -f migrations/add_user_blocking.sql
```

Or use your database management tool to execute the SQL script.

### Blocking a User (Admin)

**Via API** (requires admin key):

```bash
curl -X POST "https://python-smart-kids.vercel.app/users/{user_uid}/block" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Non-payment: Subscription expired",
    "blocked_by": "admin_name",
    "notes": "User notified via email",
    "admin_key": "YOUR_ADMIN_KEY"
  }'
```

**Via Python**:
```python
import requests

response = requests.post(
    "https://python-smart-kids.vercel.app/users/{user_uid}/block",
    json={
        "reason": "Terms of service violation",
        "blocked_by": "admin_system",
        "notes": "Detected abuse",
        "admin_key": "YOUR_ADMIN_KEY"
    }
)
print(response.json())
```

### Unblocking a User (Admin)

```bash
curl -X POST "https://python-smart-kids.vercel.app/users/{user_uid}/unblock" \
  -H "Content-Type: application/json" \
  -d '{
    "unblocked_by": "admin_name",
    "notes": "Payment received",
    "admin_key": "YOUR_ADMIN_KEY"
  }'
```

### Checking User Status (Public)

```bash
curl "https://python-smart-kids.vercel.app/users/{user_uid}/status"
```

Response:
```json
{
  "user_uid": "FrhUjcQpTDVKK14K4y3thVcPgQd2",
  "is_blocked": true,
  "blocked_reason": "Subscription expired - please renew"
}
```

### Getting Blocking History (Admin)

```bash
curl "https://python-smart-kids.vercel.app/users/{user_uid}/blocking-history?admin_key=YOUR_ADMIN_KEY&limit=10"
```

### Getting All Blocked Users (Admin)

```bash
curl "https://python-smart-kids.vercel.app/admin/blocked-users?admin_key=YOUR_ADMIN_KEY&limit=100"
```

## Common Blocking Reasons

Use these standard reason messages for consistency:

1. **Non-Payment**: `"Subscription expired - please renew"`
2. **Rule Violation**: `"Terms of service violation detected"`
3. **Abuse**: `"Unusual activity detected - account suspended"`
4. **Security**: `"Security concerns - account under review"`
5. **Fraud**: `"Fraudulent activity detected"`
6. **Temporary**: `"Temporary suspension for review"`

## User Experience

When a blocked user tries to access the application:

1. **On Login**: User is authenticated via Firebase, then blocking status is checked
2. **On Question Generation**: Blocking check occurs before generating questions
3. **Blocking Popup**: User sees a professional message with:
   - Clear "Account Blocked" heading
   - The specific reason for blocking
   - Contact support button (WhatsApp)

4. **Session Cleared**: User's local session is cleared and they're signed out

## Security Features

1. **Admin Authentication**: All admin endpoints require an admin key
2. **Fail Open**: If blocking check fails, access is allowed (better UX)
3. **Logging**: All blocking actions are logged for audit
4. **History Tracking**: Complete history of all blocking actions
5. **Middleware Protection**: Automatic blocking checks on all requests

## Environment Variables

Set the following environment variable:

```bash
ADMIN_KEY=your-secure-admin-key-here
```

For development, the default is `dev-admin-key`.

## Testing

### Test Blocking Flow

1. Create a test user
2. Block the user via API
3. Try to log in as the blocked user
4. Verify blocking popup appears
5. Verify user cannot generate questions
6. Unblock the user
7. Verify user can access normally

### Test API Endpoints

```bash
# Check status (should work without admin key)
curl "http://localhost:8000/users/test_uid/status"

# Block user (requires admin key)
curl -X POST "http://localhost:8000/users/test_uid/block" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test", "blocked_by": "admin", "admin_key": "dev-admin-key"}'

# Verify user is blocked
curl "http://localhost:8000/users/test_uid/status"

# Unblock user
curl -X POST "http://localhost:8000/users/test_uid/unblock" \
  -H "Content-Type: application/json" \
  -d '{"unblocked_by": "admin", "admin_key": "dev-admin-key"}'
```

## Monitoring

### Check Blocked Users

Regularly check for blocked users:

```python
import requests

response = requests.get(
    "https://python-smart-kids.vercel.app/admin/blocked-users",
    params={"admin_key": "YOUR_ADMIN_KEY", "limit": 100}
)

blocked_users = response.json()
print(f"Total blocked users: {len(blocked_users)}")

for user in blocked_users:
    print(f"- {user['email']}: {user['blocked_reason']}")
```

### Audit Blocking History

```python
import requests

response = requests.get(
    f"https://python-smart-kids.vercel.app/users/{user_uid}/blocking-history",
    params={"admin_key": "YOUR_ADMIN_KEY", "limit": 50}
)

history = response.json()
for record in history:
    print(f"{record['action']} at {record['blocked_at']} by {record['blocked_by']}")
    print(f"  Reason: {record['reason']}")
```

## Troubleshooting

### User Claims They're Blocked Incorrectly

1. Check blocking history:
   ```bash
   curl "https://python-smart-kids.vercel.app/users/{user_uid}/blocking-history?admin_key=YOUR_ADMIN_KEY"
   ```

2. Review the reason and notes
3. If incorrect, unblock the user
4. Document the incident in notes when unblocking

### Blocking Check Not Working

1. Verify middleware is added in `app/main.py`
2. Check logs for errors
3. Verify database schema is updated
4. Test the `/users/{uid}/status` endpoint directly

### User Not Seeing Blocking Popup

1. Check browser console for JavaScript errors
2. Verify `apiHelper.js` has `checkUserStatus()` method
3. Verify `mathQuestions.js` has blocking check methods
4. Clear browser cache and reload

## Best Practices

1. **Always Provide Clear Reasons**: Users should understand why they're blocked
2. **Document Actions**: Use the notes field to track why action was taken
3. **Regular Reviews**: Periodically review blocked users
4. **Quick Response**: Have a process to handle incorrect blocks quickly
5. **Communication**: Notify users via email when blocking (implement separately)
6. **Escalation**: Have a process for users to appeal blocks

## Future Enhancements

Consider implementing:
- Email notifications on blocking/unblocking
- Automated blocking based on rules (e.g., payment failure)
- Temporary blocks with automatic expiration
- Admin dashboard UI for managing blocked users
- Role-based admin permissions
- Blocking analytics and reporting
- Integration with payment system for automatic blocking
