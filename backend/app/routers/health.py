import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from backend.app.config import app_settings
from backend.app.schemas.health import HealthResponse

logger = logging.getLogger("pathify.health")

router = APIRouter(tags=["Health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db)):
    """Health check verifying API responsiveness, live database connectivity, and email service readiness."""
    try:
        await session.execute(text("SELECT 1"))
        email_status = "configured" if bool(app_settings.resend_api_key.strip()) else "unconfigured"
        return HealthResponse(
            status="ok",
            database="connected",
            email_service=email_status,
            message="AI Career Roadmap API and PostgreSQL are running smoothly",
        )
    except Exception as e:
        logger.exception(f"Health check database connectivity failure: {e}")
        detail_msg = (
            f"Database connectivity check failed: {str(e)}"
            if app_settings.debug
            else "Database connectivity check failed."
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "disconnected",
                "message": detail_msg,
            },
        )
