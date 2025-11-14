"""
User Blocking Middleware
Checks if a user is blocked before processing requests.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.services.user_blocking_service import UserBlockingService
from app.db.models import get_session

logger = logging.getLogger(__name__)


class UserBlockingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check if user is blocked before processing requests.
    Blocks access to protected endpoints if user is blocked.
    """
    
    # Paths that don't require blocking checks
    EXEMPT_PATHS = [
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/users/register",
        "/users/login",
        "/health",
    ]
    
    # Path patterns that are exempt (prefix matching)
    EXEMPT_PATH_PREFIXES = [
        "/users/",  # Allow status checks and other user endpoints
        "/admin/",  # Allow admin endpoints
    ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request and check if user is blocked.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware or route handler
            
        Returns:
            Response from next handler or 403 if user is blocked
        """
        # Skip blocking check for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Extract user_uid from request
        user_uid = self._extract_user_uid(request)
        
        if user_uid:
            # Check if user is blocked
            try:
                db = get_session()
                is_blocked, reason = UserBlockingService.is_user_blocked(db, user_uid)
                db.close()
                
                if is_blocked:
                    logger.warning(f"Blocked user {user_uid} attempted to access {request.url.path}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "USER_BLOCKED",
                            "message": f"Your account has been blocked. Reason: {reason}",
                            "reason": reason,
                            "user_uid": user_uid
                        }
                    )
            except Exception as e:
                # Fail open - allow access if check fails (better UX)
                logger.error(f"Error checking user blocking status: {e}")
        
        # User not blocked or no user_uid - continue with request
        response = await call_next(request)
        return response
    
    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if path is exempt from blocking checks.
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt, False otherwise
        """
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True
        
        # Prefix match
        for prefix in self.EXEMPT_PATH_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_user_uid(self, request: Request) -> str:
        """
        Extract user UID from request.
        Checks headers, query parameters, and request body.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            User UID or empty string if not found
        """
        # Check header
        user_uid = request.headers.get("X-User-UID") or request.headers.get("x-user-uid")
        if user_uid:
            return user_uid
        
        # Check query parameter
        user_uid = request.query_params.get("uid")
        if user_uid:
            return user_uid
        
        # Check path parameter (e.g., /generate-questions with uid in path)
        if "uid" in request.path_params:
            return request.path_params.get("uid")
        
        return ""
