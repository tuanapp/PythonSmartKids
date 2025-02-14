from fastapi import FastAPI
from app.api import routes

app = FastAPI(title="Math Learning API")

app.include_router(routes.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Math Learning API"}
