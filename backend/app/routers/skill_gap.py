from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from backend.app.schemas.skill_gap import SkillGapRequest, SkillGapResponse
from backend.app.services.role_service import get_role_by_id_or_slug
from backend.app.services.skill_gap_service import compute_skill_gap

router = APIRouter(tags=["Skill Gap Analysis"])


@router.post("/api/skill-gap", response_model=SkillGapResponse)
async def analyze_skill_gap(
    payload: SkillGapRequest, session: AsyncSession = Depends(get_db)
):
    """Analyze skill readiness for a given role against a submitted list of skills."""
    if not payload.roleId or not payload.roleId.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="roleId must be specified",
        )

    role = await get_role_by_id_or_slug(session, payload.roleId.strip())
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Career role '{payload.roleId}' not found",
        )

    return compute_skill_gap(role, payload.skills)
