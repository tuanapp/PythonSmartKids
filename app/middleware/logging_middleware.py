"""
Logging Middleware
Logs all requests and responses when DebugMode is enabled.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool
from app.config import DEBUG_MODE

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests and responses when DEBUG_MODE is True.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request, log details if debug mode is on.
        """
        if not DEBUG_MODE:
            return await call_next(request)

        # Log Request
        try:
            body = await request.body()
            logger.info(f"Request: {request.method} {request.url}")
            if body:
                logger.info(f"Request Body: {body.decode('utf-8', errors='replace')}")
            
            # Restore body for next handler
            # We need to create a new receive function that returns the body we just read
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")

        response = await call_next(request)

        # Log Response
        try:
            logger.info(f"Response Status: {response.status_code}")
            
            # Capture response body
            # Note: This reads the entire response into memory, which might be bad for large files
            # But for API JSON responses it should be fine.
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            
            if response_body:
                full_body = b''.join(response_body)
                logger.info(f"Response Body: {full_body.decode('utf-8', errors='replace')}")
                
        except Exception as e:
            logger.error(f"Error logging response: {e}")

        return response
