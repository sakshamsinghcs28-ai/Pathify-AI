import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models import User
from backend.app.dependencies import get_current_user
from backend.app.schemas.skill_gap import (
    SkillGapRequest,
    SkillGapResponse,
    AssessmentHistoryResponse,
)
from backend.app.services.role_service import get_role_by_id_or_slug
from backend.app.services.skill_gap_service import (
    compute_skill_assessment,
    save_skill_assessment,
    get_user_assessment_history,
    get_assessment_by_id,
)

router = APIRouter(tags=["Career Skill Assessment"])


@router.post("/api/skill-gap", response_model=SkillGapResponse, summary="Run intelligent career skill assessment")
@router.post("/api/skill-gap/assess", response_model=SkillGapResponse, summary="Run intelligent career skill assessment (alias)")
async def analyze_skill_gap(
    payload: SkillGapRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform intelligent weighted skill assessment against career requirements:
    - 4 proficiency levels: Beginner, Intermediate, Advanced, Expert
    - Weighted scoring using real database requirement levels and importance
    - Priority classification for missing skills (High, Medium, Low)
    - Optional project & internship experience assessment
    - Personalized recommendations
    - Auto-persists to PostgreSQL skill_gap_assessments for authenticated users
    """
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

    # 1. Compute intelligent weighted assessment
    assessment_result = compute_skill_assessment(
        role=role,
        raw_skills=payload.skills,
        experience=payload.experience,
    )

    # 2. Persist to PostgreSQL for the authenticated user
    record = await save_skill_assessment(
        session=session,
        user=current_user,
        role=role,
        assessment=assessment_result,
    )
    assessment_result.assessmentId = str(record.id)
    assessment_result.createdAt = record.created_at.isoformat() if record.created_at else None

    return assessment_result


@router.get("/api/skill-gap/history", response_model=AssessmentHistoryResponse, summary="Get past skill assessments")
async def get_assessment_history(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve history of previous career skill assessments for authenticated user."""
    return await get_user_assessment_history(session, current_user.id, limit=limit)


@router.get("/api/skill-gap/assessments/{assessment_id}", response_model=SkillGapResponse, summary="Get assessment by ID")
async def get_single_assessment(
    assessment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full breakdown of a past assessment by ID."""
    try:
        val_id = uuid.UUID(assessment_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment UUID format",
        )

    assessment = await get_assessment_by_id(session, val_id, current_user.id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found or does not belong to current user",
        )

    return assessment
