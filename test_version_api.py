"""
Test script for App Version API endpoints
Run this to verify the version checking logic works correctly.
"""

import sys
sys.path.insert(0, '.')

# Test the version router directly without full app context
from app.api.version import get_version_config, AppVersionResponse

def test_version_config():
    """Test version configuration retrieval"""
    print("=" * 50)
    print("Testing Version Configuration")
    print("=" * 50)
    
    config = get_version_config()
    print(f"Latest Version Code: {config['latest_version_code']}")
    print(f"Latest Version Name: {config['latest_version_name']}")
    print(f"Minimum Version Code: {config['minimum_version_code']}")
    print(f"Minimum Version Name: {config['minimum_version_name']}")
    print(f"Update URL: {config['update_url']}")
    print()

def test_version_logic():
    """Test version comparison logic"""
    print("=" * 50)
    print("Testing Version Check Logic")
    print("=" * 50)
    
    config = get_version_config()
    latest = config['latest_version_code']
    minimum = config['minimum_version_code']
    
    test_cases = [
        (1010, "Very old version"),
        (1014, "Just below minimum"),
        (1015, "At minimum"),
        (1016, "Between minimum and latest"),
        (1017, "At latest"),
        (1020, "Newer than latest"),
    ]
    
    print(f"Latest: {latest}, Minimum: {minimum}")
    print("-" * 50)
    
    for version_code, description in test_cases:
        needs_update = version_code < latest
        force_update = version_code < minimum
        
        status = "🔴 FORCE UPDATE" if force_update else ("🟡 UPDATE AVAILABLE" if needs_update else "🟢 UP TO DATE")
        print(f"Version {version_code} ({description}): {status}")
    
    print()

def test_response_model():
    """Test the response model"""
    print("=" * 50)
    print("Testing Response Model")
    print("=" * 50)
    
    config = get_version_config()
    
    response = AppVersionResponse(
        latest_version_code=config["latest_version_code"],
        latest_version_name=config["latest_version_name"],
        minimum_version_code=config["minimum_version_code"],
        minimum_version_name=config["minimum_version_name"],
        force_update=False,
        update_url=config["update_url"],
        release_notes=config["release_notes"],
    )
    
    print(f"Response: {response.model_dump_json(indent=2)}")
    print()

def simulate_api_check(version_code: int):
    """Simulate what the API endpoint would return"""
    config = get_version_config()
    
    needs_update = version_code < config["latest_version_code"]
    force_update = version_code < config["minimum_version_code"]
    
    return {
        "needs_update": needs_update,
        "force_update": force_update,
        "current_version_code": version_code,
        "latest_version_code": config["latest_version_code"],
        "latest_version_name": config["latest_version_name"],
        "minimum_version_code": config["minimum_version_code"],
        "minimum_version_name": config["minimum_version_name"],
        "update_url": config["update_url"],
        "release_notes": config["release_notes"] if needs_update else None,
    }

def test_api_simulation():
    """Test simulated API responses"""
    print("=" * 50)
    print("Simulated API Responses")
    print("=" * 50)
    
    import json
    
    # Test old version (force update required)
    print("\n📱 Client version 1010 (very old):")
    print(json.dumps(simulate_api_check(1010), indent=2))
    
    # Test slightly outdated (optional update)
    print("\n📱 Client version 1016 (optional update):")
    print(json.dumps(simulate_api_check(1016), indent=2))
    
    # Test current version
    print("\n📱 Client version 1017 (up to date):")
    print(json.dumps(simulate_api_check(1017), indent=2))

if __name__ == "__main__":
    print("\n🔧 SmartBoy App Version API Test\n")
    
    test_version_config()
    test_version_logic()
    test_response_model()
    test_api_simulation()
    
    print("=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)
