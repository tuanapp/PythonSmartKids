from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="Math Learning API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.debug("FastAPI application starting up...")

app.include_router(routes.router)

@app.get("/")
def root():
    logger.debug("Root endpoint accessed")
    return {"message": "Welcome to the Math Learning API"}
