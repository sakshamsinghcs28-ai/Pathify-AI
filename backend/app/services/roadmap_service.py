import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from database.models import (
    CareerRole,
    Skill,
    Roadmap,
    RoadmapMilestone,
    RoadmapTask,
    UserTaskProgress,
)
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
    session: AsyncSession, profile_id: str, target_role_id: Optional[str] = None
) -> ProfileRoadmapResponse:
    """Generate ordered roadmap steps for all missing skills in a student's profile.

    Syncs milestones with PostgreSQL so milestone completion status persists.
    """
    profile = await get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    chosen_role_id = target_role_id or profile.targetRoleId
    role = await get_role_by_id_or_slug(session, chosen_role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{chosen_role_id}' not found for profile",
        )

    user_uuid = uuid.UUID(profile.userId) if profile.userId else uuid.UUID(profile.id)

    user_skill_set = {s.strip().lower() for s in profile.skills}
    required_reqs = [req for req in role.skill_requirements if req.skill]

    missing_reqs = [
        req for req in required_reqs if req.skill.name.strip().lower() not in user_skill_set
    ]

    # Prioritize missing requirements according to actual career requirements:
    # 1. importance == 'required' with highest required_level
    # 2. importance == 'recommended'
    # 3. importance == 'optional'
    prio_map = {"required": 0, "recommended": 1, "optional": 2}
    missing_reqs = sorted(
        missing_reqs,
        key=lambda r: (
            prio_map.get((r.importance or "required").lower(), 1),
            -(r.required_level or 3),
            r.skill.name,
        ),
    )

    # Find or create Roadmap for this user and specific career role
    rm_query = (
        select(Roadmap)
        .where((Roadmap.user_id == user_uuid) & (Roadmap.role_id == role.id))
        .options(
            selectinload(Roadmap.milestones).selectinload(RoadmapMilestone.tasks)
        )
    )
    rm_res = await session.execute(rm_query)
    roadmap = rm_res.scalar_one_or_none()
    if not roadmap:
        roadmap = Roadmap(
            user_id=user_uuid,
            role_id=role.id,
            title=f"{role.title} Career Roadmap",
            status="active",
        )
        session.add(roadmap)
        await session.flush()
        rm_res = await session.execute(rm_query)
        roadmap = rm_res.scalar_one()

    # Map existing milestones by skill name (stored in title)
    existing_by_title = {
        m.title.lower(): m for m in (roadmap.milestones or [])
    }
    missing_skill_names_lower = {
        req.skill.name.strip().lower() for req in missing_reqs
    }

    # Delete any stale milestones no longer in missing skills
    for m in list(roadmap.milestones or []):
        if m.title.lower() not in missing_skill_names_lower:
            await session.delete(m)

    steps: List[RoadmapStep] = []
    for idx, req in enumerate(missing_reqs, start=1):
        skill = req.skill
        skill_name = skill.name.strip()
        goal, task, duration = parse_skill_curriculum(skill_name, skill.description)

        milestone = existing_by_title.get(skill_name.lower())
        if not milestone:
            milestone = RoadmapMilestone(
                roadmap_id=roadmap.id,
                sequence_order=idx,
                title=skill_name,
            )
            session.add(milestone)
            await session.flush()

            task_obj = RoadmapTask(
                milestone_id=milestone.id,
                sequence_order=1,
                title=task,
                description=goal,
                estimated_hours=10,
                status="pending",
            )
            session.add(task_obj)
            await session.flush()
            is_completed = False
        else:
            milestone.sequence_order = idx
            if not milestone.tasks:
                task_obj = RoadmapTask(
                    milestone_id=milestone.id,
                    sequence_order=1,
                    title=task,
                    description=goal,
                    estimated_hours=10,
                    status="pending",
                )
                session.add(task_obj)
                await session.flush()
                is_completed = False
            else:
                task_obj = milestone.tasks[0]
                is_completed = (task_obj.status == "completed")

        imp_str = (req.importance or "required").strip().lower()
        lvl_int = req.required_level or 3
        if imp_str == "required" and lvl_int >= 3:
            prio = "High"
        elif imp_str == "recommended" or lvl_int == 2:
            prio = "Medium"
        else:
            prio = "Low"

        steps.append(
            RoadmapStep(
                stepNumber=idx,
                skill=skill_name,
                learningGoal=goal,
                practiceTask=task,
                estimatedDuration=duration,
                completed=is_completed,
                priority=prio,
                importance=imp_str,
            )
        )

    await session.commit()

    total_required = len(required_reqs)
    acquired_count = total_required - len(missing_reqs)
    completed_milestones = sum(1 for s in steps if s.completed)
    missing_steps_count = max(0, len(steps) - completed_milestones)
    completion_pct = round((completed_milestones / len(steps)) * 100) if steps else 100

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
            missingSkillsCount=missing_steps_count,
            totalRoadmapSteps=len(steps),
            completedMilestonesCount=completed_milestones,
            completionPercentage=completion_pct,
        ),
        roadmap=steps,
    )


async def toggle_profile_roadmap_milestone(
    session: AsyncSession,
    profile_id: str,
    step_number: int,
    role_id: Optional[str] = None,
    completed: Optional[bool] = None,
) -> ProfileRoadmapResponse:
    """Toggle or set milestone completion in PostgreSQL, updating RoadmapTask and UserTaskProgress."""
    profile = await get_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    chosen_role_id = role_id or profile.targetRoleId
    role = await get_role_by_id_or_slug(session, chosen_role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{chosen_role_id}' not found",
        )

    user_uuid = uuid.UUID(profile.userId) if profile.userId else uuid.UUID(profile.id)

    # Ensure roadmap and milestones exist
    await generate_profile_roadmap(session, profile_id, target_role_id=chosen_role_id)

    rm_query = (
        select(Roadmap)
        .where((Roadmap.user_id == user_uuid) & (Roadmap.role_id == role.id))
        .options(
            selectinload(Roadmap.milestones).selectinload(RoadmapMilestone.tasks)
        )
    )
    rm_res = await session.execute(rm_query)
    roadmap = rm_res.scalar_one_or_none()
    if not roadmap or not roadmap.milestones:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap milestones found to toggle",
        )

    # Find milestone by sequence_order == step_number
    target_milestone = next(
        (m for m in roadmap.milestones if m.sequence_order == step_number),
        None,
    )
    if not target_milestone:
        sorted_milestones = sorted(roadmap.milestones, key=lambda m: m.sequence_order)
        if 1 <= step_number <= len(sorted_milestones):
            target_milestone = sorted_milestones[step_number - 1]
        elif 0 <= step_number < len(sorted_milestones):
            target_milestone = sorted_milestones[step_number]

    if not target_milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roadmap milestone for step {step_number} not found",
        )

    task = target_milestone.tasks[0] if target_milestone.tasks else None
    if not task:
        task = RoadmapTask(
            milestone_id=target_milestone.id,
            sequence_order=1,
            title=f"Practice {target_milestone.title}",
            description="Complete learning milestone",
            estimated_hours=10,
            status="pending",
        )
        session.add(task)
        await session.flush()

    if completed is not None:
        new_status = "completed" if completed else "pending"
    else:
        new_status = "pending" if task.status == "completed" else "completed"

    task.status = new_status

    # Also update or insert user_task_progress
    prog_query = select(UserTaskProgress).where(
        (UserTaskProgress.user_id == user_uuid) & (UserTaskProgress.task_id == task.id)
    )
    prog_res = await session.execute(prog_query)
    prog = prog_res.scalar_one_or_none()
    if prog:
        prog.status = new_status
        prog.progress_percent = 100 if new_status == "completed" else 0
    else:
        prog = UserTaskProgress(
            user_id=user_uuid,
            task_id=task.id,
            status=new_status,
            progress_percent=100 if new_status == "completed" else 0,
        )
        session.add(prog)

    await session.commit()

    return await generate_profile_roadmap(session, profile_id, target_role_id=chosen_role_id)
