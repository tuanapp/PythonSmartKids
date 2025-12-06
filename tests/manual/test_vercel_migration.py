"""
Test the Vercel migration system for user blocking
"""
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.vercel_migrations import migration_manager

def test_migration():
    """Test the user blocking migration"""
    
    print("=" * 60)
    print("Testing Vercel Migration System - User Blocking")
    print("=" * 60)
    print()
    
    # Check migration status
    print("1. Checking migration status...")
    status = migration_manager.check_migration_status()
    
    print(f"   Current version: {status.get('current_version')}")
    print(f"   User blocking exists: {status.get('user_blocking_exists')}")
    print(f"   User blocking history exists: {status.get('user_blocking_history_exists')}")
    print(f"   Needs migration: {status.get('needs_migration')}")
    print()
    
    if status.get('needs_migration'):
        print("2. Applying migrations...")
        result = migration_manager.apply_all_migrations()
        
        if result['success']:
            print(f"   ✓ {result['message']}")
            print()
            print("   Migrations applied:")
            for migration in result.get('migrations_applied', []):
                print(f"     - {migration}")
            print()
            
            # Check status again
            print("3. Verifying migration...")
            new_status = migration_manager.check_migration_status()
            print(f"   Current version: {new_status.get('current_version')}")
            print(f"   User blocking exists: {new_status.get('user_blocking_exists')}")
            print(f"   User blocking history exists: {new_status.get('user_blocking_history_exists')}")
            print(f"   Needs migration: {new_status.get('needs_migration')}")
            
            if not new_status.get('needs_migration'):
                print()
                print("=" * 60)
                print("✅ Migration test successful!")
                print("=" * 60)
                return True
            else:
                print()
                print("⚠ Migration applied but status still shows needs_migration")
                return False
        else:
            print(f"   ✗ Migration failed: {result.get('error')}")
            return False
    else:
        print("2. No migration needed - everything is up to date!")
        print()
        print("=" * 60)
        print("✅ All migrations already applied!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = test_migration()
    sys.exit(0 if success else 1)
