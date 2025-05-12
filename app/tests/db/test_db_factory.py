import pytest
from unittest.mock import patch, MagicMock
import os
from app.db.db_factory import DatabaseFactory
from app.db.neon_provider import NeonProvider

@pytest.fixture(autouse=True)
def reset_factory():
    """Reset the DatabaseFactory singleton instance before each test."""
    DatabaseFactory._instance = None
    yield

@patch('app.db.neon_provider.psycopg2.connect')
def test_get_provider_returns_neon(mock_connect):
    """Test that the factory returns a Neon provider by default"""
    # Setup mock connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Mock environment variables
    env_vars = {
        'NEON_DBNAME': 'test_db',
        'NEON_USER': 'test_user',
        'NEON_PASSWORD': 'test_password',
        'NEON_HOST': 'test_host'
    }
    
    with patch.dict(os.environ, env_vars):
        provider = DatabaseFactory.get_provider()
        assert isinstance(provider, NeonProvider)
        
        # Verify connection was attempted with correct parameters
        mock_connect.assert_called_once_with(
            dbname='test_db',
            user='test_user',
            password='test_password',
            host='test_host',
            sslmode='require'
        )

@patch('app.db.db_factory.DATABASE_PROVIDER', 'neon')
def test_get_provider_with_missing_env_vars():
    """Test that the factory handles missing environment variables"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(Exception) as exc_info:
            DatabaseFactory.get_provider()
        assert "Missing required environment variables" in str(exc_info.value)