from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db)):
    """Health check verifying API responsiveness and live database connectivity."""
    await session.execute(text("SELECT 1"))
    return HealthResponse()
