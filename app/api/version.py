"""
App Version API - Provides version information and update requirements
"""

from fastapi import APIRouter
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class AppVersionResponse(BaseModel):
    """Response model for app version endpoint"""
    latest_version_code: int
    latest_version_name: str
    minimum_version_code: int
    minimum_version_name: str
    force_update: bool
    update_url: str
    release_notes: str | None = None


# Version configuration - can be updated via environment variables
def get_version_config() -> dict:
    """Get version configuration from environment or defaults"""
    return {
        # Latest available version
        "latest_version_code": int(os.getenv("LATEST_APP_VERSION_CODE", "1016")),
        "latest_version_name": os.getenv("LATEST_APP_VERSION_NAME", "1.0.0.16"),
        # Minimum required version (users below this MUST update)
        "minimum_version_code": int(os.getenv("MINIMUM_APP_VERSION_CODE", "1015")),
        "minimum_version_name": os.getenv("MINIMUM_APP_VERSION_NAME", "1.0.0.15"),
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
        - latest_version_code: The newest available version code
        - latest_version_name: The newest available version name
        - minimum_version_code: Minimum version code required to use the app
        - minimum_version_name: Minimum version name required
        - force_update: True if user's version is below minimum
        - update_url: URL to update the app (Play Store)
        - release_notes: Optional notes about the latest version
    """
    config = get_version_config()
    
    return AppVersionResponse(
        latest_version_code=config["latest_version_code"],
        latest_version_name=config["latest_version_name"],
        minimum_version_code=config["minimum_version_code"],
        minimum_version_name=config["minimum_version_name"],
        force_update=False,  # Client will determine this based on their version
        update_url=config["update_url"],
        release_notes=config["release_notes"],
    )


@router.get("/app/version/check/{version_code}")
async def check_version(version_code: int):
    """
    Check if a specific version code needs to update.
    
    Args:
        version_code: The client's current version code
        
    Returns:
        - needs_update: True if there's a newer version
        - force_update: True if the client MUST update (below minimum)
        - current_version_code: The client's version
        - latest_version_code: The newest available version
        - minimum_version_code: The minimum required version
        - update_url: URL to update the app
    """
    config = get_version_config()
    
    needs_update = version_code < config["latest_version_code"]
    force_update = version_code < config["minimum_version_code"]
    
    logger.info(
        f"Version check: client={version_code}, "
        f"latest={config['latest_version_code']}, "
        f"minimum={config['minimum_version_code']}, "
        f"force={force_update}"
    )
    
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
