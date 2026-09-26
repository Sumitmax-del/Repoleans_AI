import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import health
from backend.routers import analyze
from backend.routers import chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Absolute path to frontend/dist so it works regardless of working directory.
_HERE = Path(__file__).parent          # backend/
_DIST = _HERE.parent / "frontend" / "dist"
_INDEX = _DIST / "index.html"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RepoLens API",
    description="AI-powered repository understanding and developer onboarding tool",
    version="0.1.0",
)

# Keep CORS for the Vite dev server (used during `npm run dev` development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routers  (registered before static files so /api/* is never shadowed)
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(chat.router)

# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------

# Serve the compiled Vite assets (JS, CSS, images) at /assets/*.
# Only mounted when the dist directory exists; this keeps `uvicorn backend.main:app`
# working even before the first `npm run build`.
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """
        SPA catch-all: return index.html for every non-API path so that
        client-side routing (React) works when navigating directly to a URL.
        API routes above this handler take priority because FastAPI evaluates
        routes in registration order.
        """
        return FileResponse(str(_INDEX))
