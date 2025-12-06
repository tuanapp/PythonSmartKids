# Development Setup Guide

*Last Updated: December 2025*

This guide covers setting up and running SmartBoy backend for local development.

## Quick Start

```powershell
cd Backend_Python
.\start-dev.ps1
```

Server runs at: http://localhost:8000

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (local or use Neon cloud)
- **Git**

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/tuanapp/SmartBoy.git
cd SmartBoy/Backend_Python
```

### 2. Create Virtual Environment

```powershell
python -m venv .
Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env.development` (or copy from template):

```bash
# Environment
ENVIRONMENT=development

# Database - Local PostgreSQL
DATABASE_PROVIDER=neon
NEON_DBNAME=smartboy_dev
NEON_USER=smartboy_dev
NEON_PASSWORD=smartboy_dev
NEON_HOST=localhost
NEON_SSLMODE=disable

# AI Service (optional for testing)
FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
FORGE_API_KEY=your-key
FORGE_AI_MODEL=Gemini/models/gemini-2.0-flash

# Admin
ADMIN_KEY=dev-admin-key
```

### 5. Setup Local PostgreSQL

**Automatic** (app creates database if not exists):
```powershell
.\start-dev.ps1
```

**Manual** (if needed):
```powershell
.\setup-postgres.ps1
```

Or using psql:
```sql
CREATE DATABASE smartboy_dev;
CREATE USER smartboy_dev WITH PASSWORD 'smartboy_dev';
GRANT ALL PRIVILEGES ON DATABASE smartboy_dev TO smartboy_dev;
```

### 6. Start Development Server

```powershell
.\start-dev.ps1
```

---

## Development Workflow

### Starting the Server

**Using PowerShell script (recommended)**:
```powershell
.\start-dev.ps1
```

**Using Python directly**:
```powershell
$env:ENVIRONMENT = "development"
Scripts\python.exe -m uvicorn app.main:app --host localhost --port 8000 --reload
```

### Accessing the API

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | API root |
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc documentation |

### Testing API Endpoints

**Using Swagger UI**:
1. Go to http://localhost:8000/docs
2. Click endpoint to expand
3. Click "Try it out"
4. Fill parameters and execute

**Using curl**:
```bash
# Health check
curl http://localhost:8000/

# Get user
curl http://localhost:8000/users/test-uid

# Generate questions
curl -X POST http://localhost:8000/generate-questions \
  -H "Content-Type: application/json" \
  -d '{"uid": "test-uid", "level": 1, "is_live": 0}'
```

---

## Environment Switching

### Development Mode
```powershell
.\start-dev.ps1
# Uses .env.development
# Local PostgreSQL
# Auto-reload enabled
```

### Production Mode (Local Testing)
```powershell
.\start-prod.ps1
# Uses .env.production
# Neon cloud database
# Auto-reload disabled
```

### Using Environment Manager
```python
# Check current environment
python env_manager.py status

# Switch environments
python env_manager.py dev
python env_manager.py prod

# Start server
python env_manager.py start
```

---

## Running Tests

### All Tests
```bash
pytest tests/
```

### By Category
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Real service tests (requires connections)
pytest tests/real/ -m real
```

### Specific Tests
```bash
# Single file
pytest tests/unit/test_response_validator.py

# Single test
pytest tests/unit/test_response_validator.py::test_valid_response

# With verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x
```

### Test Markers
```bash
# Quick tests only
pytest -m "not slow"

# Skip real external service tests
pytest -m "not real"
```

---

## Project Structure

```
Backend_Python/
├── app/                     # Main application
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Configuration
│   ├── api/
│   │   └── routes.py       # API endpoints
│   ├── db/
│   │   ├── db_factory.py   # Database factory
│   │   ├── db_interface.py # Abstract interface
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── neon_provider.py # PostgreSQL provider
│   │   └── vercel_migrations.py
│   ├── models/
│   │   └── schemas.py      # Pydantic schemas
│   ├── repositories/
│   │   └── db_service.py   # Data access layer
│   ├── services/
│   │   ├── ai_service.py   # AI integration
│   │   ├── prompt_service.py # Prompt tracking
│   │   └── user_blocking_service.py
│   └── middleware/
│       └── user_blocking_middleware.py
├── tests/                   # Test suites
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── real/
│   └── manual/
├── docs/                    # Documentation
├── migrations/              # Alembic migrations
├── .env                     # Environment variables
├── .env.development         # Dev environment
├── .env.production          # Prod environment
├── requirements.txt         # Dependencies
├── start-dev.ps1           # Dev server script
├── start-prod.ps1          # Prod server script
└── setup-postgres.ps1      # DB setup script
```

---

## Common Tasks

### Add New Endpoint

1. **Define schema** in `app/models/schemas.py`:
```python
class MyRequest(BaseModel):
    field: str
```

2. **Add route** in `app/api/routes.py`:
```python
@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest):
    return {"result": "success"}
```

3. **Test** at http://localhost:8000/docs

### Add Database Model

1. **Define model** in `app/db/models.py`:
```python
class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

2. **Add migration** in `app/db/vercel_migrations.py`

3. **Apply migration**:
```bash
curl -X POST "http://localhost:8000/admin/apply-migrations?admin_key=dev-admin-key"
```

### Debug Database Issues

```sql
-- Connect to database
psql -h localhost -U smartboy_dev -d smartboy_dev

-- View tables
\dt

-- Check specific table
\d users

-- Query data
SELECT * FROM users LIMIT 5;
```

---

## Troubleshooting

### Server Won't Start

**Check Python version**:
```bash
python --version  # Should be 3.11+
```

**Check virtual environment**:
```powershell
Scripts\Activate.ps1
```

**Check dependencies**:
```bash
pip install -r requirements.txt
```

### Database Connection Failed

**Check PostgreSQL is running**:
```powershell
Get-Service postgresql*
```

**Check database exists**:
```bash
psql -U postgres -c "\l"
```

**Run setup script**:
```powershell
.\setup-postgres.ps1
```

### Import Errors

**Ensure virtual environment is active**:
```powershell
Scripts\Activate.ps1
pip install -r requirements.txt
```

### Port Already in Use

**Kill existing process**:
```powershell
# Find process on port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F
```

### Tests Failing

**Run with verbose output**:
```bash
pytest tests/ -v --tb=long
```

**Check test database**:
```bash
pytest tests/integration/ -v
```

---

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- Python Test Explorer

Recommended settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "./Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true
}
```

### PyCharm

1. Set interpreter to `Scripts/python.exe`
2. Mark `app/` as Sources Root
3. Configure pytest as test runner

---

## Best Practices

1. **Always activate virtual environment** before working
2. **Run tests** before committing changes
3. **Use `.env.development`** for local config
4. **Don't commit secrets** to repository
5. **Test migrations locally** before deploying
6. **Use meaningful commit messages**

---

*For deployment information, see [DEPLOYMENT.md](DEPLOYMENT.md)*
*For database details, see [DATABASE.md](DATABASE.md)*
