# Pytest configuration file for PythonSmartKids test suite
import sys
import os
import pytest

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure pytest markers
def pytest_configure(config):
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "unit: Unit tests for isolated components")
    config.addinivalue_line("markers", "integration: Integration tests for multiple components")
    config.addinivalue_line("markers", "e2e: End-to-end tests for full system")
    config.addinivalue_line("markers", "real: Tests that use real external services")
    config.addinivalue_line("markers", "manual: Manual test scripts for development")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")
    config.addinivalue_line("markers", "neon: Tests that require Neon database connection")
