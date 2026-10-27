from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from database.models import CareerRole, Skill
from backend.app.schemas.roadmap import (
    RoadmapStep,
    RoadmapSummary,
    ProfileRoadmapResponse,
)
from backend.app.services.profile_service import get_profile_by_id
from backend.app.services.role_service import get_role_by_id_or_slug


def parse_skill_curriculum(skill_name: str, description: str | None) -> Tuple[str, str, str]:
    """Extract learningGoal, practiceTask, and estimatedDuration from skill metadata or provide realistic curriculum."""
    if description and "Goal:" in description and "Task:" in description:
        parts = [p.strip() for p in description.split("|")]
        goal = next((p.replace("Goal:", "").strip() for p in parts if p.startswith("Goal:")), "")
        task = next((p.replace("Task:", "").strip() for p in parts if p.startswith("Task:")), "")
        duration = next((p.replace("Duration:", "").strip() for p in parts if p.startswith("Duration:")), "")
        if goal and task and duration:
            return goal, task, duration

    return (
        f"Master core concepts, tools, and industry workflows for {skill_name}.",
        f"Build an end-to-end practical project exercising real-world patterns in {skill_name}.",
        "1-2 weeks",
    )


async def generate_profile_roadmap(
    session: AsyncSession, profile_id: str
) -> ProfileRoadmapResponse:
    """Generate ordered roadmap steps for all missing skills in a student's profile."""
    profile = await get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    role = await get_role_by_id_or_slug(session, profile.targetRoleId)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{profile.targetRoleId}' not found for profile",
        )

    user_skill_set = {s.strip().lower() for s in profile.skills}
    required_reqs = [req for req in role.skill_requirements if req.skill]

    missing_reqs = [
        req for req in required_reqs if req.skill.name.strip().lower() not in user_skill_set
    ]

    steps: List[RoadmapStep] = []
    for idx, req in enumerate(missing_reqs, start=1):
        skill = req.skill
        goal, task, duration = parse_skill_curriculum(skill.name, skill.description)
        steps.append(
            RoadmapStep(
                stepNumber=idx,
                skill=skill.name,
                learningGoal=goal,
                practiceTask=task,
                estimatedDuration=duration,
            )
        )

    total_required = len(required_reqs)
    acquired_count = total_required - len(missing_reqs)

    return ProfileRoadmapResponse(
        success=True,
        profileId=profile.id,
        studentName=profile.name,
        targetRoleId=role.slug,
        targetRoleTitle=role.title,
        notice="Temporary demo roadmap for development purposes. Not live industry data or AI-generated.",
        summary=RoadmapSummary(
            totalRequiredSkills=total_required,
            acquiredSkillsCount=acquired_count,
            missingSkillsCount=len(missing_reqs),
            totalRoadmapSteps=len(steps),
        ),
        roadmap=steps,
    )
