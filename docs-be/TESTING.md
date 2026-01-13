# Testing Guide

*Last Updated: December 2025*

This guide covers running and writing tests for the SmartBoy backend.

## Quick Start

```bash
cd Backend_Python

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific category
pytest tests/unit/
```

---

## Test Organization

```
tests/
├── unit/           # Isolated component tests
├── integration/    # Multi-component tests
├── e2e/           # End-to-end tests
├── real/          # Tests against real services
├── manual/        # Manual test scripts
├── fixtures/      # Test data
├── contract/      # API contract tests
├── conftest.py    # Pytest configuration
└── pytest_fixtures.py  # Shared fixtures
```

### Test Categories

| Category | Purpose | Speed | External Services |
|----------|---------|-------|-------------------|
| `unit/` | Test single components | Fast | No |
| `integration/` | Test component interaction | Medium | Mocked |
| `e2e/` | Test full workflows | Slow | Mocked |
| `real/` | Test actual services | Slow | Yes |
| `manual/` | Development scripts | N/A | Varies |

---

## Running Tests

### All Tests
```bash
pytest tests/
```

### By Directory
```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Real service tests
pytest tests/real/
```

### By Marker
```bash
# Quick tests (exclude slow)
pytest -m "not slow"

# Skip real external service tests
pytest -m "not real"

# Only unit tests
pytest -m unit
```

### Specific File or Test
```bash
# Single file
pytest tests/unit/test_response_validator.py

# Single test function
pytest tests/unit/test_response_validator.py::test_valid_response

# Tests matching pattern
pytest -k "test_user"
```

### With Options
```bash
# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Show print statements
pytest tests/ -s

# Parallel execution
pytest tests/ -n auto

# Coverage report
pytest tests/ --cov=app --cov-report=html
```

---

## Test Markers

Tests use pytest markers for categorization:

```python
import pytest

@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
def test_interaction():
    pass

@pytest.mark.real
def test_real_service():
    pass

@pytest.mark.slow
def test_lengthy_operation():
    pass
```

### Available Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Unit tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.e2e` | End-to-end tests |
| `@pytest.mark.real` | Real external services |
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.manual` | Manual test scripts |

---

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_my_service.py
import pytest
from app.services.my_service import MyService

class TestMyService:
    def test_process_valid_input(self):
        service = MyService()
        result = service.process("valid")
        assert result == expected_value
    
    def test_process_invalid_input_raises(self):
        service = MyService()
        with pytest.raises(ValueError):
            service.process(None)
```

### Integration Test Example

```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_questions_success():
    response = client.post(
        "/generate-questions",
        json={"uid": "test-uid", "level": 1, "is_live": 0}
    )
    assert response.status_code == 200
    assert "questions" in response.json()

def test_generate_questions_missing_uid():
    response = client.post(
        "/generate-questions",
        json={"level": 1}
    )
    assert response.status_code == 422  # Validation error
```

### Using Fixtures

```python
# tests/conftest.py
import pytest

@pytest.fixture
def test_user():
    return {
        "uid": "test-user-123",
        "email": "test@example.com",
        "name": "Test User"
    }

@pytest.fixture
def db_session():
    # Setup database session
    session = create_test_session()
    yield session
    # Cleanup
    session.rollback()
    session.close()

# Usage in test
def test_with_fixtures(test_user, db_session):
    result = save_user(db_session, test_user)
    assert result.uid == test_user["uid"]
```

---

## Test Data

### Fixtures Directory

```
tests/fixtures/
├── sample_requests.json
├── sample_responses.json
└── test_data.py
```

### Loading Test Data

```python
import json
from pathlib import Path

def load_fixture(filename):
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path) as f:
        return json.load(f)

def test_with_fixture_data():
    data = load_fixture("sample_requests.json")
    # Use data in test
```

---

## Mocking

### Mock External Services

```python
from unittest.mock import Mock, patch

@patch('app.services.ai_service.make_ai_call')
def test_generate_questions_mocked(mock_ai):
    mock_ai.return_value = {
        "questions": [{"q": "1+1=?", "a": "2"}]
    }
    
    result = generate_questions("test-uid")
    
    assert len(result["questions"]) == 1
    mock_ai.assert_called_once()
```

### Mock Database

```python
@patch('app.repositories.db_service.get_user_by_uid')
def test_with_mocked_db(mock_get_user):
    mock_get_user.return_value = {
        "uid": "test",
        "subscription": 2
    }
    
    result = check_user_access("test")
    assert result["is_premium"] == True
```

---

## Real Service Tests

Tests that require actual external services:

```python
# tests/real/test_ai_service_real.py
import pytest
import os

@pytest.mark.real
@pytest.mark.skipif(
    not os.getenv("RUN_REAL_API_TESTS"),
    reason="Real API tests disabled"
)
def test_real_ai_call():
    # This makes actual API calls
    result = make_real_ai_call()
    assert result is not None
```

### Enable Real Tests

```bash
# Set environment variable
export RUN_REAL_API_TESTS=true

# Run real tests
pytest tests/real/ -m real
```

---

## Coverage

### Generate Coverage Report

```bash
# Run with coverage
pytest tests/ --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Configuration

```ini
# pytest.ini
[pytest]
addopts = --cov=app --cov-report=term-missing

[coverage:run]
source = app
omit = 
    */tests/*
    */__pycache__/*
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -m "not real" --cov=app
```

---

## Troubleshooting

### Tests Not Found

```bash
# Ensure test files start with test_
# Ensure test functions start with test_
pytest tests/ -v --collect-only
```

### Import Errors

```bash
# Ensure virtual environment is active
Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Tests Failing

```bash
# Ensure test database exists
pytest tests/integration/ -v --tb=long
```

### Slow Tests

```bash
# Skip slow tests
pytest tests/ -m "not slow"

# Run in parallel
pytest tests/ -n auto
```

---

## Best Practices

1. **Isolate tests** - Each test should be independent
2. **Use fixtures** - Share setup code via fixtures
3. **Mock external services** - Don't rely on network in unit tests
4. **Name clearly** - `test_<what>_<condition>_<expected>`
5. **Keep fast** - Unit tests should run in milliseconds
6. **Test edge cases** - Empty inputs, nulls, boundaries
7. **Document complex tests** - Add docstrings explaining intent

---

*For more details, see [tests/TEST_SUITE_DOCUMENTATION.md](../tests/TEST_SUITE_DOCUMENTATION.md)*
