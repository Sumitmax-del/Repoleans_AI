from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness check — returns OK when the server is running."""
    return HealthResponse(status="ok", version="0.1.0")
