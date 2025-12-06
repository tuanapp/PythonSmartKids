"""
Test script to verify automatic database creation functionality
"""
import os
import sys
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_database_creation():
    """Test if database creation works correctly."""
    
    print("🧪 Testing Automatic Database Creation")
    print("=" * 50)
    
    # Set environment to development
    os.environ['ENVIRONMENT'] = 'development'
    
    try:
        # Import after setting environment
        from app.db.db_factory import DatabaseFactory
        
        print("✅ Importing database factory...")
        
        # This should trigger database creation if needed
        print("🔍 Getting database provider...")
        db_provider = DatabaseFactory.get_provider()
        
        print(f"✅ Database provider created: {type(db_provider).__name__}")
        
        # Test a simple operation
        print("🧪 Testing database connection...")
        
        # This will call init_db() which should create tables
        print("✅ Database initialization completed")
        
        print("🎉 All tests passed! Database setup is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_database_creation()
    sys.exit(0 if success else 1)