"""
Quick verification script to ensure Backend_Python works after removing performance report functionality
"""
import sys
import os

# Add Backend_Python to path
sys.path.insert(0, os.path.abspath('.'))

print("🔍 Verifying Backend_Python after performance report removal...\n")

# Test 1: Verify old service is gone
try:
    from app.services.performance_report_service import PerformanceReportService
    print("❌ Old performance_report_service still exists (should be removed)")
    sys.exit(1)
except ImportError:
    print("✅ Old performance_report_service properly removed")

# Test 2: Verify client is gone
try:
    from app.services.performance_report_client import initialize_performance_service
    print("❌ performance_report_client still exists (should be removed)")
    sys.exit(1)
except ImportError:
    print("✅ performance_report_client properly removed")

# Test 3: Check routes can be imported
try:
    from app.api.routes import router
    print("✅ API routes imported successfully")
except Exception as e:
    print(f"❌ Failed to import routes: {e}")
    sys.exit(1)

print("\n✅ All verification checks passed!")
print("\n📝 Summary:")
print("  - Performance report service removed")
print("  - Performance report client removed")
print("  - Routes functional")
print("\n🎉 Backend_Python performance report cleanup successful!")
