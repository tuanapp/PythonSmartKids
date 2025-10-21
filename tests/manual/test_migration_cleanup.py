"""
Quick test to verify migration endpoints are working after cleanup
"""
import sys
import os

# Add the Backend_Python directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.routes import router

def test_remaining_endpoints():
    """Test that only the essential migration endpoints remain"""
    
    # Get all routes from the router
    routes = [route for route in router.routes]
    
    # Get migration-related routes
    migration_routes = [
        route for route in routes 
        if hasattr(route, 'path') and 'migration' in route.path.lower()
    ]
    
    print("✅ Migration Endpoints Found:")
    print("-" * 60)
    
    essential_endpoints = []
    removed_endpoints = []
    
    for route in migration_routes:
        endpoint_info = f"{route.methods} {route.path}"
        print(f"  {endpoint_info}")
        essential_endpoints.append(route.path)
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print("=" * 60)
    
    expected_endpoints = [
        '/admin/migration-status',
        '/admin/apply-migrations'
    ]
    
    unexpected_endpoints = [
        '/admin/add-notes-column',
        '/admin/add-level-column',
        '/admin/add-prompts-table'
    ]
    
    # Check essential endpoints exist
    print("\n✅ Essential Endpoints (Should Exist):")
    for endpoint in expected_endpoints:
        exists = any(endpoint in route.path for route in migration_routes)
        status = "✓ EXISTS" if exists else "✗ MISSING"
        print(f"  {status}: {endpoint}")
    
    # Check unnecessary endpoints are removed
    print("\n❌ Unnecessary Endpoints (Should Be Removed):")
    for endpoint in unexpected_endpoints:
        exists = any(endpoint in route.path for route in migration_routes)
        status = "✗ STILL EXISTS" if exists else "✓ REMOVED"
        print(f"  {status}: {endpoint}")
    
    print("\n" + "=" * 60)
    print("✅ Cleanup verification complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_remaining_endpoints()
