# Tests Organization

This directory contains all tests for the PythonSmartKids project, organized by type and purpose.

## Directory Structure

```
tests/
├── unit/                       # Unit tests (isolated component testing)
├── integration/                # Integration tests (multiple components)
├── e2e/                        # End-to-end tests (full system)
├── manual/                     # Manual test scripts (for development)
├── fixtures/                   # Test data and fixtures
├── real/                       # Real external service tests
├── conftest.py                 # Pytest configuration
└── pytest_fixtures.py         # Shared test fixtures
```

## Running Tests

### All Tests
```bash
pytest tests/
```

### By Category
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only  
pytest tests/integration/

# Real service tests (requires actual connections)
pytest tests/real/ -m real
```

### By Markers
```bash
# Quick tests only
pytest -m "not slow"

# Skip real external service tests
pytest -m "not real"

# Run specific test types
pytest -m unit
pytest -m integration
```

### Specific Test Files
```bash
# Validator tests
pytest tests/unit/test_response_validator.py

# API tests
pytest tests/integration/test_api.py
```

## Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interaction between multiple components
- **End-to-End Tests**: Test complete user workflows
- **Manual Tests**: Scripts for manual testing and debugging
- **Real Tests**: Tests that connect to actual external services
- **Fixtures**: Shared test data and utilities

## Markers

Tests are marked with pytest markers for easy filtering:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.real` - Tests requiring real services
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.manual` - Manual test scripts
