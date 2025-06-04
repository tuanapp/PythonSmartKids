# Test Organization Plan

## Current State
Test files are scattered between:
- Root directory: Manual/integration test scripts
- app/tests/: Proper unit and integration tests

## Proposed Organization Structure

```
tests/                          # Move all tests here (root level)
├── unit/                       # Unit tests (isolated component testing)
│   ├── test_ai_service.py
│   ├── test_db_service.py
│   ├── test_validators.py
│   └── test_models.py
├── integration/                # Integration tests (multiple components)
│   ├── test_api_endpoints.py
│   ├── test_ai_service_integration.py
│   ├── test_db_integration.py
│   └── test_neon_integration.py
├── e2e/                        # End-to-end tests (full system)
│   ├── test_complete_workflow.py
│   └── test_user_scenarios.py
├── manual/                     # Manual test scripts (for development)
│   ├── test_api_endpoint.py    # (current root file)
│   ├── simple_test.py          # (current root file) 
│   ├── direct_test.py          # (current root file)
│   ├── test_exact_format.py    # (current root file)
│   └── final_comprehensive_test.py # (current root file)
├── fixtures/                   # Test data and fixtures
│   ├── test_payload.json       # (current root file)
│   ├── sample_responses.json
│   └── mock_data.py
├── real/                       # Real external service tests
│   ├── test_neon_connection_real.py
│   └── test_ai_service_real.py
└── conftest.py                 # Pytest configuration and fixtures

app/tests/                      # Remove this directory
```

## Benefits of This Structure

1. **Clear Separation**: Manual scripts vs automated tests
2. **Better Discovery**: All tests in one place
3. **Proper Categorization**: Unit, integration, e2e, manual
4. **Consistent Naming**: All automated tests use `test_` prefix
5. **Shared Fixtures**: Central location for test data
6. **Tool Integration**: Better pytest discovery and IDE support

## Migration Steps

1. Create new `tests/` directory structure
2. Move and reorganize existing test files
3. Update import paths in moved files
4. Update pytest configuration
5. Update CI/CD configuration (if any)
6. Remove old `app/tests/` directory
7. Update documentation and README

## File Categorization

### Unit Tests (tests/unit/)
- test_ai_service.py (from app/tests/unit/)
- test_response_validator.py (from app/tests/validators/)
- test_db_providers.py (from app/tests/db/)
- test_db_factory.py (from app/tests/db/)

### Integration Tests (tests/integration/)
- test_api.py (from app/tests/api/)
- test_ai_service_integration.py (from app/tests/integration/)
- test_neon_integration.py (from app/tests/integration/)
- test_db_service.py (from app/tests/db/)

### Manual Test Scripts (tests/manual/)
- test_api_endpoint.py (from root)
- simple_test.py (from root)
- direct_test.py (from root)
- test_exact_format.py (from root)
- final_comprehensive_test.py (from root)
- test_validation.py (from root)

### Real Service Tests (tests/real/)
- test_neon_connection_real.py (from app/tests/real/)
- test_ai_service_real.py (from app/tests/real/)

### Test Data (tests/fixtures/)
- test_payload.json (from root)
- Add more structured test data files
