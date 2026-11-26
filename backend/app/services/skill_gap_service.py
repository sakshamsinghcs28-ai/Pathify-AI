import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CareerRole, SkillGapAssessment, User
from backend.app.schemas.skill_gap import (
    ExperienceInput,
    ImprovingSkillDetail,
    MatchedSkillDetail,
    MissingSkillDetail,
    RecommendationDetail,
    SkillGapAnalysis,
    SkillGapResponse,
    SkillProficiencyInput,
    AssessmentHistoryItem,
    AssessmentHistoryResponse,
)

LEVEL_TO_INT: Dict[str, int] = {
    "beginner": 2,
    "intermediate": 3,
    "advanced": 4,
    "expert": 5,
}

INT_TO_LEVEL: Dict[int, str] = {
    1: "Beginner",
    2: "Beginner",
    3: "Intermediate",
    4: "Advanced",
    5: "Expert",
}

IMPORTANCE_MULTIPLIER: Dict[str, float] = {
    "required": 1.5,
    "recommended": 1.0,
    "optional": 0.7,
}


def parse_user_skills(
    raw_skills: List[Union[SkillProficiencyInput, str, dict]]
) -> Dict[str, int]:
    """Parse raw skills input (either string, SkillProficiencyInput, or dict)
    into normalized lowercase skill name -> integer proficiency level (2-5).
    """
    skill_map: Dict[str, int] = {}
    for item in raw_skills:
        if isinstance(item, str):
            clean_name = item.strip().lower()
            if clean_name:
                skill_map[clean_name] = LEVEL_TO_INT["intermediate"]
        elif isinstance(item, SkillProficiencyInput):
            clean_name = item.name.strip().lower()
            if clean_name:
                lvl_str = item.level.strip().lower()
                skill_map[clean_name] = LEVEL_TO_INT.get(lvl_str, LEVEL_TO_INT["intermediate"])
        elif isinstance(item, dict):
            name = str(item.get("name", "")).strip().lower()
            if name:
                lvl_str = str(item.get("level", "intermediate")).strip().lower()
                skill_map[name] = LEVEL_TO_INT.get(lvl_str, LEVEL_TO_INT["intermediate"])
    return skill_map


def compute_skill_assessment(
    role: CareerRole,
    raw_skills: List[Union[SkillProficiencyInput, str, dict]],
    experience: Optional[ExperienceInput] = None,
    assessment_id: Optional[str] = None,
    created_at_str: Optional[str] = None,
) -> SkillGapResponse:
    """Intelligent Career Skill Assessment Engine:
    1. Evaluates user proficiency against authoritative CareerSkillRequirement data.
    2. Calculates weighted match score based on requirement levels and importance.
    3. Categorizes gaps into Matched, Needing Improvement, and Missing (High/Medium/Low priority).
    4. Computes experience adjustments for applied projects and internships.
    5. Generates personalized learning recommendations.
    """
    user_skills_map = parse_user_skills(raw_skills)

    matched_skills_names: List[str] = []
    missing_skills_names: List[str] = []
    improving_skills_names: List[str] = []

    detailed_matched: List[MatchedSkillDetail] = []
    detailed_improving: List[ImprovingSkillDetail] = []
    detailed_missing: List[MissingSkillDetail] = []
    recommendations: List[RecommendationDetail] = []

    total_possible_weight = 0.0
    total_earned_score = 0.0

    # Sort requirements: required first, then highest level
    sorted_reqs = sorted(
        role.skill_requirements,
        key=lambda r: (
            0 if r.importance.lower() == "required" else (1 if r.importance.lower() == "recommended" else 2),
            -(r.required_level or 3),
        ),
    )

    for req in sorted_reqs:
        if not req.skill:
            continue

        skill_name = req.skill.name
        skill_slug = req.skill.slug or skill_name.lower().replace(" ", "-")
        category = req.skill.category or "technical"
        clean_req_name = skill_name.strip().lower()

        required_lvl_int = int(req.required_level) if req.required_level else 3
        required_lvl_str = INT_TO_LEVEL.get(required_lvl_int, "Intermediate")
        importance_str = (req.importance or "required").strip().lower()
        multiplier = IMPORTANCE_MULTIPLIER.get(importance_str, 1.0)

        # Weight is derived directly from requirement's importance and required level
        skill_weight = round(multiplier * required_lvl_int, 2)
        total_possible_weight += skill_weight

        # Check if user has this skill
        user_lvl_int = user_skills_map.get(clean_req_name, 0)

        if user_lvl_int >= required_lvl_int:
            # 1. FULLY MATCHED
            total_earned_score += skill_weight
            matched_skills_names.append(skill_name)
            detailed_matched.append(
                MatchedSkillDetail(
                    name=skill_name,
                    userLevel=INT_TO_LEVEL.get(user_lvl_int, "Intermediate"),
                    requiredLevel=required_lvl_str,
                    category=category,
                    scoreWeight=skill_weight,
                    importance=importance_str,
                )
            )
        elif user_lvl_int > 0:
            # 2. NEEDS IMPROVEMENT (User has skill but below target level)
            gap = required_lvl_int - user_lvl_int
            earned = round(skill_weight * (user_lvl_int / required_lvl_int), 2)
            total_earned_score += earned
            improving_skills_names.append(skill_name)
            detailed_improving.append(
                ImprovingSkillDetail(
                    name=skill_name,
                    userLevel=INT_TO_LEVEL.get(user_lvl_int, "Beginner"),
                    requiredLevel=required_lvl_str,
                    gap=gap,
                    category=category,
                    scoreWeight=skill_weight,
                    importance=importance_str,
                )
            )
            # Add targeted recommendation for improvement
            hours = gap * 15
            recommendations.append(
                RecommendationDetail(
                    skill=skill_name,
                    priority="High" if importance_str == "required" else "Medium",
                    type="upskill_level",
                    action=f"Upskill {skill_name} from {INT_TO_LEVEL.get(user_lvl_int, 'Beginner')} to {required_lvl_str} by implementing production-grade features.",
                    estimatedHours=hours,
                )
            )
        else:
            # 3. COMPLETELY MISSING
            missing_skills_names.append(skill_name)

            # Categorize into High, Medium, Low priority
            if importance_str == "required" and required_lvl_int >= 3:
                priority = "High"
                hours = required_lvl_int * 12
                action = f"Core foundation for {role.title}: complete structured courses and hands-on milestones in {skill_name}."
            elif importance_str == "recommended" or required_lvl_int == 2:
                priority = "Medium"
                hours = required_lvl_int * 10
                action = f"Industry recommended competence: build practical portfolio components showcasing {skill_name}."
            else:
                priority = "Low"
                hours = required_lvl_int * 6
                action = f"Elective enhancement: familiarize yourself with {skill_name} syntax and architectural concepts."

            detailed_missing.append(
                MissingSkillDetail(
                    name=skill_name,
                    requiredLevel=required_lvl_str,
                    priority=priority,
                    importance=importance_str,
                    category=category,
                    scoreWeight=skill_weight,
                )
            )
            recommendations.append(
                RecommendationDetail(
                    skill=skill_name,
                    priority=priority,
                    type="acquire_missing",
                    action=action,
                    estimatedHours=hours,
                )
            )

    # Calculate Base Technical Score
    if total_possible_weight > 0:
        base_technical_score = round((total_earned_score / total_possible_weight) * 100, 1)
    else:
        base_technical_score = 0.0

    # Calculate Experience Bonus
    experience_bonus = 0.0
    if experience:
        # Projects: +2% per project up to max 6%
        proj_bonus = min(6.0, experience.projectsCount * 2.0)
        # Internships: +1% per month up to max 6%
        intern_bonus = min(6.0, experience.internshipMonths * 1.0)
        # Combined experience adjustment capped at 10%
        experience_bonus = round(min(10.0, proj_bonus + intern_bonus), 1)

    # Final Readiness Score (bounded between 0 and 100)
    final_readiness_score = round(min(100.0, base_technical_score + experience_bonus), 1)
    match_percentage = f"{int(round(final_readiness_score))}%"

    # Dynamic explanation
    total_req_count = len(sorted_reqs)
    matched_count = len(matched_skills_names)
    improving_count = len(improving_skills_names)
    missing_count = len(missing_skills_names)

    exp_note = f" (includes +{experience_bonus}% applied project/internship bonus)" if experience_bonus > 0 else ""
    explanation = (
        f"Weighted Career Readiness: {match_percentage}{exp_note}. "
        f"You have {matched_count} fully matched skill(s), {improving_count} skill(s) needing level up, "
        f"and {missing_count} missing skill(s) out of {total_req_count} industry requirements for {role.title}."
    )

    # Sort recommendations: High priority first, then Medium, then Low
    prio_order = {"High": 0, "Medium": 1, "Low": 2}
    recommendations.sort(key=lambda r: prio_order.get(r.priority, 3))

    analysis = SkillGapAnalysis(
        totalRequiredSkills=total_req_count,
        matchedCount=matched_count,
        missingCount=missing_count,
        improvingCount=improving_count,
        matchPercentage=match_percentage,
        explanation=explanation,
        readinessScore=final_readiness_score,
        baseTechnicalScore=base_technical_score,
        experienceBonus=experience_bonus,
        weightedScore=round(total_earned_score, 2),
        totalPossibleWeight=round(total_possible_weight, 2),
    )

    return SkillGapResponse(
        success=True,
        roleId=role.slug,
        roleTitle=role.title,
        assessmentId=assessment_id,
        createdAt=created_at_str,
        analysis=analysis,
        matchedSkills=matched_skills_names,
        missingSkills=missing_skills_names,
        improvingSkills=improving_skills_names,
        detailedMatched=detailed_matched,
        detailedImproving=detailed_improving,
        detailedMissing=detailed_missing,
        recommendations=recommendations,
    )


def compute_skill_gap(role: CareerRole, user_skills: List[str]) -> SkillGapResponse:
    """Backward-compatible wrapper for legacy callers."""
    return compute_skill_assessment(role=role, raw_skills=user_skills)


async def save_skill_assessment(
    session: AsyncSession,
    user: User,
    role: CareerRole,
    assessment: SkillGapResponse,
) -> SkillGapAssessment:
    """Persist assessment record to PostgreSQL skill_gap_assessments table."""
    record = SkillGapAssessment(
        user_id=user.id,
        role_id=role.id,
        readiness_score=assessment.analysis.readinessScore,
        breakdown=assessment.model_dump(),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_user_assessment_history(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> AssessmentHistoryResponse:
    """Fetch previous assessments for authenticated user."""
    query = (
        select(SkillGapAssessment)
        .where(SkillGapAssessment.user_id == user_id)
        .options(selectinload(SkillGapAssessment.role))
        .order_by(SkillGapAssessment.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(query)
    records = res.scalars().all()

    items: List[AssessmentHistoryItem] = []
    for r in records:
        b = r.breakdown or {}
        a = b.get("analysis", {})
        created_str = r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat()
        items.append(
            AssessmentHistoryItem(
                id=str(r.id),
                roleId=r.role.slug if r.role else b.get("roleId", "unknown"),
                roleTitle=r.role.title if r.role else b.get("roleTitle", "Unknown Role"),
                readinessScore=float(r.readiness_score or a.get("readinessScore", 0.0)),
                matchPercentage=a.get("matchPercentage", f"{int(round(r.readiness_score or 0))}%"),
                createdAt=created_str,
                matchedCount=int(a.get("matchedCount", 0)),
                improvingCount=int(a.get("improvingCount", 0)),
                missingCount=int(a.get("missingCount", 0)),
            )
        )

    return AssessmentHistoryResponse(
        success=True,
        total=len(items),
        assessments=items,
    )


async def get_assessment_by_id(
    session: AsyncSession,
    assessment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[SkillGapResponse]:
    """Retrieve full breakdown of a single saved assessment belonging to user."""
    query = (
        select(SkillGapAssessment)
        .where(
            SkillGapAssessment.id == assessment_id,
            SkillGapAssessment.user_id == user_id,
        )
        .options(selectinload(SkillGapAssessment.role))
    )
    res = await session.execute(query)
    record = res.scalar_one_or_none()
    if not record or not record.breakdown:
        return None

    try:
        data = record.breakdown.copy()
        data["assessmentId"] = str(record.id)
        data["createdAt"] = record.created_at.isoformat() if record.created_at else None
        return SkillGapResponse(**data)
    except Exception:
        return None
