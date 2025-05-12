import pytest
import sys
from unittest.mock import patch, MagicMock
from app.db.db_factory import DatabaseFactory
from app.db.sqlite_provider import SQLiteProvider
from app.db.neon_provider import NeonProvider


class TestDatabaseFactory:
    """Tests for the DatabaseFactory class."""
    
    def setup_method(self):
        """Setup for each test."""
        # Save the original instance (if any)
        self.original_instance = DatabaseFactory._instance
        # Clear the singleton between tests
        DatabaseFactory._instance = None
    
    def teardown_method(self):
        """Teardown after each test."""
        # Restore the original instance state
        DatabaseFactory._instance = self.original_instance
    
    def test_get_provider_sqlite(self):
        """Test that get_provider returns a SQLiteProvider when configured for SQLite."""
        # Create a more comprehensive patch setup to isolate from environment
        db_provider_patcher = patch.object(sys.modules['app.config'], 'DATABASE_PROVIDER', 'sqlite')
        db_url_patcher = patch.object(sys.modules['app.config'], 'DATABASE_URL', 'sqlite:///test.db')
        
        try:
            # Start the patchers
            db_provider_patcher.start()
            db_url_patcher.start()
            
            # Re-import the module to pick up the patched settings
            import importlib
            importlib.reload(sys.modules['app.db.db_factory'])
            from app.db.db_factory import DatabaseFactory as ReloadedFactory
            
            # Now get the provider
            provider = ReloadedFactory.get_provider()
            
            assert isinstance(provider, SQLiteProvider)
            # Test that it's a singleton
            assert ReloadedFactory.get_provider() is provider
            
        finally:
            # Stop the patchers
            db_provider_patcher.stop()
            db_url_patcher.stop()
    
    def test_get_provider_neon(self):
        """Test that get_provider returns a NeonProvider when configured for Neon PostgreSQL."""
        # Create a more comprehensive patch setup
        db_provider_patcher = patch.object(sys.modules['app.config'], 'DATABASE_PROVIDER', 'neon')
        neon_dbname_patcher = patch.object(sys.modules['app.config'], 'NEON_DBNAME', 'test_db')
        neon_user_patcher = patch.object(sys.modules['app.config'], 'NEON_USER', 'test_user')
        neon_password_patcher = patch.object(sys.modules['app.config'], 'NEON_PASSWORD', 'test_password')
        neon_host_patcher = patch.object(sys.modules['app.config'], 'NEON_HOST', 'test.host.com')
        neon_sslmode_patcher = patch.object(sys.modules['app.config'], 'NEON_SSLMODE', 'require')
        
        try:
            # Start the patchers
            db_provider_patcher.start()
            neon_dbname_patcher.start()
            neon_user_patcher.start()
            neon_password_patcher.start()
            neon_host_patcher.start()
            neon_sslmode_patcher.start()
            
            # Re-import to pick up patched settings
            import importlib
            importlib.reload(sys.modules['app.db.db_factory'])
            from app.db.db_factory import DatabaseFactory as ReloadedFactory
            
            # Use patch to avoid actually connecting to Neon PostgreSQL
            with patch('app.db.neon_provider.psycopg2.connect', return_value=MagicMock()):
                with patch('app.db.neon_provider.NeonProvider.init_db', return_value=None):
                    provider = ReloadedFactory.get_provider()
                    
                    assert isinstance(provider, NeonProvider)
                    # Test that it's a singleton
                    assert ReloadedFactory.get_provider() is provider
                
        finally:
            # Stop the patchers
            db_provider_patcher.stop()
            neon_dbname_patcher.stop()
            neon_user_patcher.stop()
            neon_password_patcher.stop()
            neon_host_patcher.stop()
            neon_sslmode_patcher.stop()
    
    def test_get_provider_invalid(self):
        """Test that get_provider raises an error for invalid provider types."""
        # Create a patch for an invalid provider
        db_provider_patcher = patch.object(sys.modules['app.config'], 'DATABASE_PROVIDER', 'invalid')
        
        try:
            # Start the patcher
            db_provider_patcher.start()
            
            # Re-import to pick up patched settings
            import importlib
            importlib.reload(sys.modules['app.db.db_factory'])
            from app.db.db_factory import DatabaseFactory as ReloadedFactory
            
            with pytest.raises(ValueError) as excinfo:
                ReloadedFactory.get_provider()
            
            assert "Unsupported database provider" in str(excinfo.value)
            
        finally:
            # Stop the patcher
            db_provider_patcher.stop()