# Architecture Overview

*Last Updated: December 2025*

This document describes the SmartBoy backend architecture, design decisions, and code organization.

## System Overview

SmartBoy is an AI-powered educational platform that:
- Generates personalized math practice questions using AI
- Tracks student performance and attempts
- Manages user subscriptions and daily limits
- Supports user blocking for admin control

### Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL (Neon cloud) |
| Deployment | Vercel (serverless) |
| AI Service | TensorBlock Forge / OpenRouter |
| Auth | Firebase (frontend) |

---

## Layered Architecture

```
┌─────────────────────────────────────────┐
│           API Layer (routes.py)          │
│         FastAPI endpoints & routing      │
├─────────────────────────────────────────┤
│         Service Layer (services/)        │
│    Business logic & AI integration       │
├─────────────────────────────────────────┤
│       Repository Layer (repositories/)   │
│       Data access abstraction            │
├─────────────────────────────────────────┤
│         Database Layer (db/)             │
│     SQLAlchemy models & providers        │
└─────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **API** | `app/api/routes.py` | HTTP endpoints, request validation, response formatting |
| **Service** | `app/services/` | Business logic, AI calls, limit enforcement |
| **Repository** | `app/repositories/` | Database operations abstraction |
| **Database** | `app/db/` | Models, providers, migrations |
| **Middleware** | `app/middleware/` | Request interceptors (blocking, auth) |
| **Models** | `app/models/` | Pydantic schemas for API |

---

## Code Organization

```
app/
├── main.py              # FastAPI app initialization
├── config.py            # Environment configuration
│
├── api/
│   ├── routes.py        # All API endpoints
│   └── version.py       # App version info
│
├── db/
│   ├── db_factory.py    # Provider factory pattern
│   ├── db_interface.py  # Abstract database interface
│   ├── db_init.py       # Database initialization
│   ├── models.py        # SQLAlchemy ORM models
│   ├── neon_provider.py # PostgreSQL implementation
│   └── vercel_migrations.py  # Migration system
│
├── models/
│   └── schemas.py       # Pydantic request/response schemas
│
├── repositories/
│   └── db_service.py    # Data access layer
│
├── services/
│   ├── ai_service.py    # AI/LLM integration
│   ├── llm_service.py   # Multi-provider LLM management
│   ├── prompt_service.py # Prompt tracking & limits
│   └── user_blocking_service.py
│
├── middleware/
│   └── user_blocking_middleware.py
│
├── utils/
│   └── logger.py        # Logging utilities
│
└── validators/
    └── response_validator.py  # AI response validation
```

---

## Database Design

### Provider Pattern

The database layer uses a provider pattern for abstraction:

```python
# Abstract interface (db_interface.py)
class DatabaseProvider(ABC):
    @abstractmethod
    def init_db(self): pass
    
    @abstractmethod
    def save_attempt(self, attempt): pass
    
    @abstractmethod
    def get_attempts_by_uid(self, uid): pass

# Concrete implementation (neon_provider.py)
class NeonProvider(DatabaseProvider):
    def init_db(self):
        # PostgreSQL-specific implementation
        pass
```

### Factory Pattern

```python
# db_factory.py
class DatabaseFactory:
    @staticmethod
    def get_provider() -> DatabaseProvider:
        provider = os.getenv("DATABASE_PROVIDER", "neon")
        if provider == "neon":
            return NeonProvider()
        raise ValueError(f"Unknown provider: {provider}")
```

### Data Flow

```
API Request
    ↓
routes.py (validation, routing)
    ↓
services/*.py (business logic)
    ↓
db_service.py (repository)
    ↓
db_factory.py → neon_provider.py
    ↓
PostgreSQL Database
```

---

## Key Design Decisions

### 1. Simplified Prompt Tracking (Migration 008)

**Problem**: Originally had separate tables (`prompts`, `question_generations`, `llm_interactions`) tracking similar data.

**Solution**: Consolidated all LLM tracking into single `prompts` table.

**Benefits**:
- Single source of truth
- ~700 lines of code removed
- Simpler queries (no JOINs)
- Easier maintenance

```python
# Daily counting - now uses prompts table directly
def get_daily_question_generation_count(uid, date):
    SELECT COUNT(*) FROM prompts
    WHERE uid = %s 
      AND request_type = 'question_generation'
      AND DATE(created_at) = DATE(%s)
```

### 2. Vercel-Compatible Migrations

**Problem**: Alembic doesn't work with Vercel's serverless architecture (read-only filesystem).

**Solution**: HTTP-based migration system.

```python
# vercel_migrations.py
class VercelMigrationManager:
    def apply_all_migrations(self):
        # Creates tables, adds columns, creates indexes
        # Idempotent - safe to run multiple times
        pass
```

**Usage**:
```bash
curl -X POST ".../admin/apply-migrations?admin_key=KEY"
```

### 3. Subscription-Based Limits

**Problem**: Need to limit free users while allowing premium unlimited access.

**Solution**: Server-side enforcement with local caching.

```python
# PromptService.can_generate_questions()
def can_generate_questions(uid, subscription, max_daily=2):
    if subscription >= 2:  # Premium
        return {"can_generate": True, "is_premium": True}
    
    count = self.get_daily_question_generation_count(uid)
    return {
        "can_generate": count < max_daily,
        "current_count": count,
        "max_count": max_daily
    }
```

### 4. User Blocking Middleware

**Problem**: Need to block users system-wide (payment issues, violations).

**Solution**: Middleware that checks blocking status on every request.

```python
# user_blocking_middleware.py
class UserBlockingMiddleware:
    async def __call__(self, request, call_next):
        uid = extract_uid_from_request(request)
        if is_user_blocked(uid):
            return JSONResponse(status_code=403, ...)
        return await call_next(request)
```

### 5. Multi-Provider LLM Service (Migration 012)

**Problem**: Need flexible AI model management with multiple providers (Google, Groq, Anthropic).

**Solution**: Database-driven model configuration with automatic Forge API routing.

**Architecture**:
```
AI Request → get_models_to_try() → Ordered Model List → Forge API → Provider (Google/Groq)
                                         ↓
                                   llm_models table
                                   (order_number)
```

**Provider Configuration** (`llm_service.py`):
```python
SUPPORTED_PROVIDERS = {
    'google': {
        'forge_prefix': 'tensorblock',  # Forge routes to Google
        'api_url': 'https://generativelanguage.googleapis.com/...'
    },
    'groq': {
        'forge_prefix': 'Groq',  # Forge routes to Groq
        'api_url': 'https://api.groq.com/...'
    }
}
```

**Database-Driven Model Selection**:
```sql
-- Models ordered by priority
SELECT model_name, provider FROM llm_models
WHERE active = TRUE AND deprecated = FALSE
ORDER BY order_number ASC
-- Returns: [('llama-3.3-70b-versatile', 'groq'), ('gemini-2.0-flash', 'google'), ...]
```

**Forge API Format**:
```python
# DB: model_name='llama-3.3-70b-versatile', provider='groq'
# Formatted as: 'Groq/llama-3.3-70b-versatile'

# DB: model_name='gemini-2.0-flash', provider='google'  
# Formatted as: 'tensorblock/gemini-2.0-flash'
```

**Model Fallback Chain**:
1. Try models in `order_number` sequence
2. If all fail, use `FORGE_FALLBACK_MODEL_1` (env var)
3. Return error if all options exhausted

**Benefits**:
- **Zero code changes** to add new models - just database config
- **Automatic failover** between providers
- **Centralized model management** via admin API
- **24-hour caching** to minimize DB queries
- **API sync** to auto-update available models

**Admin Operations**:
```bash
# Sync models from provider API
POST /admin/sync-llm-models?provider=groq&admin_key=KEY

# Get all models
GET /llm-models

# Update model priority
PUT /admin/llm-model/{model_name}
```

See [GROQ_INTEGRATION.md](../../docs/GROQ_INTEGRATION.md) for complete provider integration guide.

---

## API Design

### Endpoint Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| `GET /resource/{id}` | `/users/{uid}` | Get single resource |
| `POST /resource` | `/submit_attempt` | Create resource |
| `POST /action` | `/generate-questions` | Trigger action |
| `GET /admin/...` | `/admin/migration-status` | Admin operations |

### Request/Response Schemas

Defined in `app/models/schemas.py`:

```python
class GenerateQuestionsRequest(BaseModel):
    uid: str
    level: Optional[int] = None
    is_live: Optional[int] = 1  # 1=app, 0=test
    
    # Optional AI config overrides
    ai_bridge_base_url: Optional[str] = None
    ai_bridge_api_key: Optional[str] = None
    ai_bridge_model: Optional[str] = None
```

### Error Handling

```python
@router.post("/endpoint")
async def endpoint(request):
    try:
        # Business logic
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")
```

---

## AI Integration

### Service Flow

```
User Request
    ↓
routes.py: Generate questions
    ↓
ai_service.py: generate_practice_questions()
    ↓
Build prompt from:
  - User attempts history
  - Question patterns (filtered by level)
  - System instructions
    ↓
Call AI API (TensorBlock/OpenRouter)
    ↓
Validate response (response_validator.py)
    ↓
prompt_service.py: record_prompt()
  - Track tokens, cost, timing
  - Store request/response
    ↓
Return questions to user
```

### LLM Tracking

Every AI call is tracked in `prompts` table:

| Field | Purpose |
|-------|---------|
| `request_text` | Full prompt sent |
| `response_text` | AI response |
| `model_name` | Which model used |
| `prompt_tokens` | Input tokens |
| `completion_tokens` | Output tokens |
| `estimated_cost_usd` | Cost calculation |
| `response_time_ms` | Latency |
| `status` | success/error/timeout |
| `level` | Difficulty level requested |
| `source` | 'api', 'cached', 'fallback' |

---

## Configuration

### Environment Variables

Loaded via `config.py`:

```python
DATABASE_PROVIDER = os.getenv("DATABASE_PROVIDER", "neon")
NEON_DBNAME = os.getenv("NEON_DBNAME", "smartboydb")
ADMIN_KEY = os.getenv("ADMIN_KEY", "dev-admin-key")
FORGE_API_KEY = os.getenv("FORGE_API_KEY", "")
```

### Multi-Environment

| File | Environment |
|------|-------------|
| `.env.development` | Local development |
| `.env.production` | Production settings |
| Vercel Dashboard | Production secrets |

---

## Security

### Admin Authentication

Admin endpoints require `admin_key` parameter:

```python
@router.post("/admin/apply-migrations")
async def apply_migrations(admin_key: str = ""):
    expected = os.getenv('ADMIN_KEY', 'dev-admin-key')
    if admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid admin key")
```

### User Blocking

Blocked users receive 403 Forbidden:

```python
{
    "is_blocked": true,
    "blocked_reason": "Subscription expired"
}
```

### Database Security

- SSL required for production (`NEON_SSLMODE=require`)
- Connection pooling handled by Neon
- No raw SQL in API layer (use repository)

---

## Performance Considerations

### Database

- **Indexes** on frequently queried columns (`uid`, `created_at`)
- **Connection pooling** via Neon
- **Query limits** (e.g., `MAX_ATTEMPTS_HISTORY_LIMIT`)

### API

- **Serverless** - scales automatically
- **Cold starts** - first request slower
- **Caching** - consider for read-heavy endpoints

### AI Calls

- **Timeout handling** - don't wait forever
- **Fallback responses** - handle AI failures gracefully
- **Cost tracking** - monitor usage in prompts table

---

## Future Considerations

1. **Caching layer** - Redis for session data
2. **Rate limiting** - Protect AI endpoints
3. **WebSocket** - Real-time features
4. **Background jobs** - Async processing
5. **Multi-tenancy** - School/class support

---

*For implementation details, see individual module files.*
*For API details, see [API_REFERENCE.md](API_REFERENCE.md)*
