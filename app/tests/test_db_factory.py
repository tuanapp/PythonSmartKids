import pytest
import sys
from unittest.mock import patch, MagicMock
from app.db.db_factory import DatabaseFactory
from app.db.sqlite_provider import SQLiteProvider
from app.db.supabase_provider import SupabaseProvider


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
    
    def test_get_provider_supabase(self):
        """Test that get_provider returns a SupabaseProvider when configured for Supabase."""
        # Create a more comprehensive patch setup
        db_provider_patcher = patch.object(sys.modules['app.config'], 'DATABASE_PROVIDER', 'supabase')
        supabase_url_patcher = patch.object(sys.modules['app.config'], 'SUPABASE_URL', 'https://test.supabase.co')
        supabase_key_patcher = patch.object(sys.modules['app.config'], 'SUPABASE_KEY', 'test_key')
        
        try:
            # Start the patchers
            db_provider_patcher.start()
            supabase_url_patcher.start()
            supabase_key_patcher.start()
            
            # Re-import to pick up patched settings
            import importlib
            importlib.reload(sys.modules['app.db.db_factory'])
            from app.db.db_factory import DatabaseFactory as ReloadedFactory
            
            # Use patch to avoid actually connecting to Supabase
            with patch('app.db.supabase_provider.create_client', return_value=MagicMock()):
                with patch('app.db.supabase_provider.SupabaseProvider.init_db', return_value=None):
                    provider = ReloadedFactory.get_provider()
                    
                    assert isinstance(provider, SupabaseProvider)
                    # Test that it's a singleton
                    assert ReloadedFactory.get_provider() is provider
                
        finally:
            # Stop the patchers
            db_provider_patcher.stop()
            supabase_url_patcher.stop()
            supabase_key_patcher.stop()
    
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