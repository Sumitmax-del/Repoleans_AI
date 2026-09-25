import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import health
from backend.routers import analyze

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(
    title="RepoLens API",
    description="AI-powered repository understanding and developer onboarding tool",
    version="0.1.0",
)

# Allow the Vite dev server to call the API during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(analyze.router)
# Future routers (added in subsequent sub-tasks):
# app.include_router(chat.router, prefix="/api")
