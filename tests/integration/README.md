# Integration Tests README

This document explains how to run and understand the integration tests for the SmartBoy Backend API.

## Prerequisites

Before running integration tests, ensure you have:

1. **PostgreSQL Database Setup**
   - Local PostgreSQL server running (for development tests)
   - Database `smartboy_dev` created with proper permissions
   - User `smartboy_dev` with access to the database

2. **Environment Setup**
   - Python virtual environment activated
   - All dependencies installed (`pip install -r requirements.txt`)
   - Environment variables configured in `.env.development`

3. **Database Initialization**
   - Run the database creation test to ensure tables exist:
     ```powershell
     cd Backend_Python
     $env:ENVIRONMENT = "development"
     .\Scripts\python.exe test_db_creation.py
     ```

## Running Integration Tests

### User Registration Integration Test

This comprehensive test verifies the complete user registration flow from API to database storage and retrieval.

```powershell
cd Backend_Python
$env:ENVIRONMENT = "development"
.\Scripts\python.exe -m pytest tests\integration\test_user_registration_integration.py -v
```

### What This Test Covers

The `test_user_registration_integration.py` runs 10 comprehensive tests:

1. **API Registration Test** - Verifies `/users/register` endpoint accepts and processes user data
2. **Database Storage Verification** - Confirms user data is correctly saved to PostgreSQL 
3. **Data Retrieval by UID** - Tests retrieving user data using Firebase UID
4. **Data Retrieval by Email** - Tests retrieving user data using email address
5. **User Update Test** - Verifies existing user updates (upsert functionality)
6. **Database Update Verification** - Confirms user updates are saved correctly
7. **Invalid Data Validation** - Tests API rejection of malformed requests
8. **Grade Level Validation** - Tests all valid grade levels (4, 5, 6, 7)
9. **Concurrent Registrations** - Tests multiple user registrations without conflicts
10. **Email Uniqueness Handling** - Verifies multiple users can have same email (Firebase manages uniqueness)

### Expected Output

Successful test run should show:
```
========================================== 10 passed, 3 warnings in ~3s ==========================================
```

With detailed output showing:
- ✅ API responses with user data
- ✅ Database records with all fields saved correctly
- ✅ Successful data retrieval operations
- ✅ Proper validation error handling

## Running All Integration Tests

To run all integration tests in the suite:

```powershell
cd Backend_Python
$env:ENVIRONMENT = "development"
.\Scripts\python.exe -m pytest tests\integration\ -v
```

## Running Specific Test Categories

### Database Connection Tests
```powershell
.\Scripts\python.exe -m pytest tests\integration\test_db_connection.py -v
```

### API Endpoint Tests
```powershell
.\Scripts\python.exe -m pytest tests\integration\test_api.py -v
```

### Database Service Tests
```powershell
.\Scripts\python.exe -m pytest tests\integration\test_db_service.py -v
```

## Test Data and Cleanup

### Test Data
Integration tests create test data in the development database including:
- Test users with realistic Firebase UIDs (28 character alphanumeric strings like "FrhUjcQpTDVKK14K4y3thVcPgQd2")
- Test users with various grade levels (4, 5, 6, 7)
- Multiple registration scenarios
- Update/upsert test cases

### Cleanup
Currently, test data is left in the database for manual inspection. To clean up test data:

```sql
-- Connect to smartboy_dev database
-- Clean up integration test users (they use realistic Firebase UID format)
DELETE FROM users WHERE uid IN (
    'FrhUjcQpTDVKK14K4y3thVcPgQd2',
    'Abc1Def2Ghi3Jkl4Mno5Pqr6Stu7',
    'Bcd2Efg3Hij4Klm5Nop6Qrs7Tuv8', 
    'Cde3Fgh4Ijk5Lmn6Opq7Rst8Uvw9',
    'Def4Ghi5Jkl6Mno7Pqr8Stu9Vwx0'
);

-- Or clean up all test users if needed
DELETE FROM users WHERE email LIKE '%.test@%' OR email LIKE 'test.%@%' OR email LIKE '%@example.com';
```

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```
Error: Database connection failed
```
**Solution:** Ensure PostgreSQL is running and `smartboy_dev` database exists:
```powershell
# Check PostgreSQL service
Get-Service postgresql*

# Create database if needed
.\setup-postgres.ps1
```

**2. Import Errors**
```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Ensure you're in the `Backend_Python` directory and environment is set:
```powershell
cd Backend_Python
$env:ENVIRONMENT = "development"
```

**3. Permission Denied**
```
Error: permission denied for schema public
```
**Solution:** Grant proper permissions to the database user:
```sql
GRANT ALL ON SCHEMA public TO smartboy_dev;
```

### Debugging Tests

To run tests with more detailed output and debugging:

```powershell
# Run with detailed output and stop on first failure
.\Scripts\python.exe -m pytest tests\integration\test_user_registration_integration.py -v -s -x

# Run specific test method
.\Scripts\python.exe -m pytest tests\integration\test_user_registration_integration.py::TestUserRegistrationIntegration::test_01_user_registration_success -v -s

# Run with Python debugging on failures
.\Scripts\python.exe -m pytest tests\integration\test_user_registration_integration.py --pdb
```

## Manual API Testing

For manual testing of the API while the server is running:

```powershell
# Start development server (in separate terminal)
.\start-dev.ps1

# Run manual API test
.\Scripts\python.exe tests\manual\test_registration_api_manual.py
```

## Test Environment Variables

The integration tests use the development environment configuration:

```bash
# .env.development
ENVIRONMENT=development
DATABASE_URL=postgresql://smartboy_dev:smartboy_dev@localhost:5432/smartboy_dev
NEON_DBNAME=smartboy_dev
NEON_USER=smartboy_dev
NEON_PASSWORD=smartboy_dev
NEON_HOST=localhost
NEON_SSLMODE=disable
```

## Integration Test Architecture

```
Integration Test Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Database      │    │   PostgreSQL    │
│   TestClient    │───▶│   Service       │───▶│   Database      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP POST     │    │   save_user_    │    │   INSERT/UPDATE │
│   /users/       │    │   registration  │    │   users table   │
│   register      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Next Steps

After successful integration tests:

1. **Run End-to-End Tests** - Test the complete frontend + backend flow
2. **Performance Testing** - Test with larger datasets
3. **Production Testing** - Run tests against production environment (Neon)
4. **CI/CD Integration** - Add tests to automated build pipeline

## Support

For issues with integration tests:
1. Check the test output for specific error messages
2. Verify database connectivity with `test_db_creation.py`
3. Ensure all environment variables are set correctly
4. Review the logs in the test output for debugging information