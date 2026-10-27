from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from backend.app.schemas.profiles import (
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileDetailResponse,
    ProfileSkillGapResponse,
)
from backend.app.schemas.roadmap import ProfileRoadmapResponse
from backend.app.services.profile_service import create_student_profile, get_profile_by_id
from backend.app.services.role_service import get_role_by_id_or_slug
from backend.app.services.skill_gap_service import compute_skill_gap
from backend.app.services.roadmap_service import generate_profile_roadmap

router = APIRouter(tags=["Student Profiles"])


@router.post(
    "/api/profiles",
    response_model=ProfileCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    payload: ProfileCreateRequest, session: AsyncSession = Depends(get_db)
):
    """Create a new student profile and initialize their career roadmap."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student name is required",
        )
    if not payload.targetRoleId or not payload.targetRoleId.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="targetRoleId is required",
        )

    profile_data = await create_student_profile(session, payload)
    return ProfileCreateResponse(success=True, profile=profile_data)


@router.get("/api/profiles/{id}", response_model=ProfileDetailResponse)
async def get_profile(id: str, session: AsyncSession = Depends(get_db)):
    """Retrieve an existing student profile by profile UUID."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )
    return ProfileDetailResponse(success=True, profile=profile_data)


@router.get("/api/profiles/{id}/skill-gap", response_model=ProfileSkillGapResponse)
async def get_profile_skill_gap(id: str, session: AsyncSession = Depends(get_db)):
    """Compute skill gap analysis for a saved student profile against their target role."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )

    role = await get_role_by_id_or_slug(session, profile_data.targetRoleId)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{profile_data.targetRoleId}' not found",
        )

    gap_result = compute_skill_gap(role, profile_data.skills)

    return ProfileSkillGapResponse(
        success=True,
        profileId=profile_data.id,
        studentName=profile_data.name,
        roleId=role.slug,
        roleTitle=role.title,
        analysis=gap_result.analysis,
        matchedSkills=gap_result.matchedSkills,
        missingSkills=gap_result.missingSkills,
    )


@router.get("/api/profiles/{id}/roadmap", response_model=ProfileRoadmapResponse)
async def get_profile_roadmap(id: str, session: AsyncSession = Depends(get_db)):
    """Retrieve learning roadmap steps for missing skills in a student profile."""
    return await generate_profile_roadmap(session, id)
