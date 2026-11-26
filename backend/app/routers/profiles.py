from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models import User
from backend.app.schemas.profiles import (
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileDetailResponse,
    ProfileSkillGapResponse,
)
from backend.app.schemas.roadmap import ProfileRoadmapResponse, RoadmapSummary, ToggleMilestoneRequest
from backend.app.services.profile_service import create_student_profile, get_profile_by_id, get_profile_by_user_id
from backend.app.services.role_service import get_role_by_id_or_slug
from backend.app.services.skill_gap_service import compute_skill_gap
from backend.app.services.roadmap_service import generate_profile_roadmap, toggle_profile_roadmap_milestone
from backend.app.dependencies import get_current_user

router = APIRouter(tags=["Student Profiles"])


@router.post(
    "/api/profiles",
    response_model=ProfileCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update student profile",
)
async def create_profile(
    payload: ProfileCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a student profile and initialize their career roadmap. Protected: requires authentication."""
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

    profile_data = await create_student_profile(
        session, payload, current_user=current_user
    )
    return ProfileCreateResponse(success=True, profile=profile_data)


@router.get(
    "/api/profiles/me",
    response_model=ProfileDetailResponse,
    summary="Get currently authenticated user's profile",
)
async def get_my_profile(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve profile data for the authenticated user derived from verified token."""
    profile_data = await get_profile_by_user_id(session, current_user.id)
    return ProfileDetailResponse(success=True, profile=profile_data)


@router.get(
    "/api/profiles/me/roadmap",
    response_model=ProfileRoadmapResponse,
    summary="Get currently authenticated user's roadmap",
)
async def get_my_roadmap(
    roleId: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve learning roadmap steps for the authenticated user."""
    profile = await get_profile_by_user_id(session, current_user.id)
    if not profile or not (roleId or profile.targetRoleId):
        return ProfileRoadmapResponse(
            success=True,
            profileId=str(profile.id if profile else current_user.id),
            studentName=profile.name if profile else (getattr(current_user, "full_name", "") or ""),
            targetRoleId=roleId or (profile.targetRoleId if profile else "") or "",
            targetRoleTitle=profile.targetRoleTitle if profile else "",
            summary=RoadmapSummary(
                totalRequiredSkills=0,
                acquiredSkillsCount=0,
                missingSkillsCount=0,
                totalRoadmapSteps=0,
                completedMilestonesCount=0,
                completionPercentage=0,
            ),
            roadmap=[],
        )
    return await generate_profile_roadmap(session, profile.id, target_role_id=roleId)


@router.post(
    "/api/profiles/me/roadmap/toggle-step",
    response_model=ProfileRoadmapResponse,
    summary="Toggle roadmap milestone for authenticated user",
)
async def toggle_my_roadmap_step(
    payload: ToggleMilestoneRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle completion status of a roadmap milestone for the authenticated user."""
    profile = await get_profile_by_user_id(session, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found for current user. Please save your profile first.",
        )
    return await toggle_profile_roadmap_milestone(
        session=session,
        profile_id=profile.id,
        step_number=payload.stepNumber,
        role_id=payload.roleId,
        completed=payload.completed,
    )


@router.get("/api/profiles/{id}", response_model=ProfileDetailResponse, summary="Get student profile by ID")
async def get_profile(
    id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve an existing student profile by profile UUID. Protected: requires authentication & ownership."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )

    if profile_data.userId != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this profile.",
        )

    return ProfileDetailResponse(success=True, profile=profile_data)


@router.get("/api/profiles/{id}/skill-gap", response_model=ProfileSkillGapResponse, summary="Get profile skill gap")
async def get_profile_skill_gap(
    id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute skill gap analysis for a saved student profile. Protected: requires authentication & ownership."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )

    if profile_data.userId != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this profile skill-gap.",
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


@router.get("/api/profiles/{id}/roadmap", response_model=ProfileRoadmapResponse, summary="Get profile roadmap")
async def get_profile_roadmap(
    id: str,
    roleId: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve learning roadmap steps for missing skills in a student profile. Protected: requires authentication & ownership."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )

    if profile_data.userId != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this roadmap.",
        )

    return await generate_profile_roadmap(session, id, target_role_id=roleId)


@router.post("/api/profiles/{id}/roadmap/toggle-step", response_model=ProfileRoadmapResponse, summary="Toggle roadmap step")
async def toggle_roadmap_step(
    id: str,
    payload: ToggleMilestoneRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle completion status of a roadmap milestone in PostgreSQL. Protected: requires authentication & ownership."""
    profile_data = await get_profile_by_id(session, id)
    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{id}' not found",
        )

    if profile_data.userId != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this roadmap.",
        )

    return await toggle_profile_roadmap_milestone(
        session=session,
        profile_id=id,
        step_number=payload.stepNumber,
        role_id=payload.roleId,
        completed=payload.completed,
    )
