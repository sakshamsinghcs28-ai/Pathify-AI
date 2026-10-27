from typing import List
from database.models import CareerRole
from backend.app.schemas.skill_gap import SkillGapAnalysis, SkillGapResponse


def compute_skill_gap(role: CareerRole, user_skills: List[str]) -> SkillGapResponse:
    """Analyze student skills against a target role's required skills."""
    # Normalized user skill lookup
    user_skill_set = {s.strip().lower() for s in user_skills if s.strip()}

    required_skills: List[str] = [
        req.skill.name for req in role.skill_requirements if req.skill
    ]

    matched_skills: List[str] = []
    missing_skills: List[str] = []

    for req_name in required_skills:
        if req_name.strip().lower() in user_skill_set:
            matched_skills.append(req_name)
        else:
            missing_skills.append(req_name)

    total_required = len(required_skills)
    matched_count = len(matched_skills)
    missing_count = len(missing_skills)

    percentage_int = int(round((matched_count / total_required * 100))) if total_required > 0 else 0
    match_percentage = f"{percentage_int}%"
    explanation = (
        f"You have {matched_count} of {total_required} required skills "
        f"({match_percentage} match). Missing {missing_count} skill(s) to reach 100%."
    )

    return SkillGapResponse(
        success=True,
        roleId=role.slug,
        roleTitle=role.title,
        analysis=SkillGapAnalysis(
            totalRequiredSkills=total_required,
            matchedCount=matched_count,
            missingCount=missing_count,
            matchPercentage=match_percentage,
            explanation=explanation,
        ),
        matchedSkills=matched_skills,
        missingSkills=missing_skills,
    )
