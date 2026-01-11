from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.api import version as version_routes
from app.middleware.user_blocking_middleware import UserBlockingMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Suppress noisy logs from libraries
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Math Learning API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add user blocking middleware
app.add_middleware(UserBlockingMiddleware)

# Add logging middleware (logs all requests/responses if DebugMode=1)
app.add_middleware(LoggingMiddleware)

@app.on_event("startup")
async def startup_event():
    logger.debug("FastAPI application starting up...")

app.include_router(routes.router)
app.include_router(version_routes.router)

@app.get("/")
def root():
    logger.debug("Root endpoint accessed")
    return {"message": "Welcome to the Math Learning API - last updated 2025-08-25 with Forge Bridge for AI"}
