from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models import User
from backend.app.dependencies import get_current_user
from backend.app.schemas.roles import RolesResponse
from backend.app.services.role_service import get_all_roles

router = APIRouter(tags=["Career Roles"])


@router.get("/api/roles", response_model=RolesResponse)
async def list_roles(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available career roles and their required skill sets. Protected: requires authentication."""
    return await get_all_roles(session)
