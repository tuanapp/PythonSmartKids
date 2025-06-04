# Manual Test Scripts

This directory contains manual test scripts used for development, debugging, and ad-hoc testing.

## Scripts

### API Testing Scripts
- `test_api_endpoint.py` - Comprehensive API endpoint testing
- `simple_test.py` - Basic API functionality test
- `direct_test.py` - Direct API testing without client layer
- `test_exact_format.py` - Tests exact request/response format
- `final_comprehensive_test.py` - Complete end-to-end workflow test

### Validation Testing Scripts  
- `test_validation.py` - Comprehensive validator testing and debugging

## Usage

These scripts are meant to be run manually during development:

```bash
# Run from project root
cd c:\Private\GIT\PythonSmartKids

# Example: Run comprehensive API test
python tests/manual/final_comprehensive_test.py

# Example: Run simple API test
python tests/manual/simple_test.py

# Example: Run validation testing
python tests/manual/test_validation.py
```

## Requirements

- FastAPI server running on localhost:8000
- Valid OpenAI API configuration
- Network connectivity for external API calls

## Notes

- These scripts often require external services to be running
- They may make actual API calls and consume resources
- Output is typically verbose for debugging purposes
- Not included in automated test suites
