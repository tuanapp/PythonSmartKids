"""  
App Version API - Provides version information and update requirements
Now uses version NAME (e.g., "1.0.0.17") for comparison instead of version code
"""

from fastapi import APIRouter
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_version(version_str: str) -> tuple:
    """Parse version string like '1.0.0.15' into tuple (1, 0, 0, 15) for comparison"""
    try:
        parts = [int(p) for p in version_str.split('.')]
        # Pad to 4 parts for consistent comparison
        while len(parts) < 4:
            parts.append(0)
        return tuple(parts[:4])  # Only use first 4 parts
    except (ValueError, AttributeError):
        return (0, 0, 0, 0)


class AppVersionResponse(BaseModel):
    """Response model for app version endpoint"""
    latest_version: str
    minimum_version: str
    force_update: bool
    update_url: str
    release_notes: str | None = None


# Version configuration - can be updated via environment variables
def get_version_config() -> dict:
    """Get version configuration from environment or defaults"""
    return {
        # Latest available version (version NAME only)
        "latest_version": os.getenv("LATEST_APP_VERSION", "1.0.0.17"),
        # Minimum required version (users below this MUST update)
        "minimum_version": os.getenv("MINIMUM_APP_VERSION", "1.0.0.17"),
        # Play Store URL
        "update_url": os.getenv(
            "APP_UPDATE_URL", 
            "market://details?id=tuanorg.smartboy"
        ),
        # Release notes for latest version
        "release_notes": os.getenv("APP_RELEASE_NOTES", None),
    }
@router.get("/app/version", response_model=AppVersionResponse)
async def get_app_version():
    """
    Get current app version requirements.
    
    Returns:
        - latest_version: The newest available version (e.g., "1.0.0.17")
        - minimum_version: Minimum version required to use the app
        - force_update: False (client determines based on their version)
        - update_url: URL to update the app (Play Store)
        - release_notes: Optional notes about the latest version
    """
    config = get_version_config()
    
    return AppVersionResponse(
        latest_version=config["latest_version"],
        minimum_version=config["minimum_version"],
        force_update=False,  # Client will determine this based on their version
        update_url=config["update_url"],
        release_notes=config["release_notes"],
    )


@router.get("/app/version/check/{client_version:path}")
async def check_version(client_version: str):
    """
    Check if a specific version needs to update.
    Uses semantic version comparison (e.g., "1.0.0.15" < "1.0.0.17").
    
    Args:
        client_version: The client's current version string (e.g., "1.0.0.15")
        
    Returns:
        - needs_update: True if there's a newer version
        - force_update: True if the client MUST update (below minimum)
        - current_version: The client's version
        - latest_version: The newest available version
        - minimum_version: The minimum required version
        - update_url: URL to update the app
    """
    config = get_version_config()
    
    client_v = parse_version(client_version)
    latest_v = parse_version(config["latest_version"])
    minimum_v = parse_version(config["minimum_version"])
    
    needs_update = client_v < latest_v
    force_update = client_v < minimum_v
    
    logger.info(
        f"Version check: client={client_version} ({client_v}), "
        f"latest={config['latest_version']} ({latest_v}), "
        f"minimum={config['minimum_version']} ({minimum_v}), "
        f"needs_update={needs_update}, force={force_update}"
    )
    
    return {
        "needs_update": needs_update,
        "force_update": force_update,
        "current_version": client_version,
        "latest_version": config["latest_version"],
        "minimum_version": config["minimum_version"],
        "update_url": config["update_url"],
        "release_notes": config["release_notes"] if needs_update else None,
    }
