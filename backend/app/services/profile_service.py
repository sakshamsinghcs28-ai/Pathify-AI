import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from database.models import User, UserProfile, UserSkill, Skill, Roadmap, CareerRole
from backend.app.schemas.profiles import ProfileCreateRequest, ProfileData
from backend.app.services.role_service import get_role_by_id_or_slug


async def create_student_profile(
    session: AsyncSession, data: ProfileCreateRequest
) -> ProfileData:
    """Create a student user, profile, linked skills, and target role roadmap in PostgreSQL."""
    role = await get_role_by_id_or_slug(session, data.targetRoleId)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{data.targetRoleId}' not found",
        )

    # 1. Create student User
    synthetic_email = f"student_{uuid.uuid4().hex[:12]}@pathify.local"
    user = User(
        email=synthetic_email,
        role="student",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    # 2. Create UserProfile
    profile = UserProfile(
        user_id=user.id,
        full_name=data.name.strip(),
        education=data.education.strip() if data.education else None,
    )
    session.add(profile)
    await session.flush()

    # 3. Create active Roadmap
    roadmap = Roadmap(
        user_id=user.id,
        role_id=role.id,
        title=f"{role.title} Career Roadmap",
        status="active",
    )
    session.add(roadmap)

    # 4. Save User Skills
    saved_skill_names = []
    if data.skills:
        # Load all existing skills for fast lookup
        skills_res = await session.execute(select(Skill))
        skill_cache = {s.name.lower(): s for s in skills_res.scalars().all()}

        for skill_name in data.skills:
            clean_name = skill_name.strip()
            if not clean_name:
                continue
            key = clean_name.lower()
            if key in skill_cache:
                sk = skill_cache[key]
            else:
                slug = key.replace(" ", "-").replace("&", "and").replace("/", "-")
                sk = Skill(slug=slug, name=clean_name, category="technical")
                session.add(sk)
                await session.flush()
                skill_cache[key] = sk

            user_skill = UserSkill(
                user_id=user.id,
                skill_id=sk.id,
                proficiency_level=3,
                verified=False,
            )
            session.add(user_skill)
            saved_skill_names.append(sk.name)

    await session.commit()

    return ProfileData(
        id=str(profile.id),
        name=profile.full_name or "",
        education=profile.education,
        skills=saved_skill_names,
        targetRoleId=role.slug,
        targetRoleTitle=role.title,
        createdAt=profile.created_at.isoformat().replace("+00:00", "Z"),
    )


async def get_profile_by_id(
    session: AsyncSession, profile_id_str: str
) -> Optional[ProfileData]:
    """Fetch profile data by profile UUID or user UUID."""
    try:
        profile_uuid = uuid.UUID(profile_id_str)
    except (ValueError, TypeError):
        return None

    # Query profile with user, user_skills, and roadmaps
    query = (
        select(UserProfile)
        .where(
            (UserProfile.id == profile_uuid) | (UserProfile.user_id == profile_uuid)
        )
        .options(
            selectinload(UserProfile.user)
            .selectinload(User.skills)
            .joinedload(UserSkill.skill),
            selectinload(UserProfile.user)
            .selectinload(User.roadmaps)
            .joinedload(Roadmap.role),
        )
    )
    res = await session.execute(query)
    profile = res.scalar_one_or_none()
    if not profile or not profile.user:
        return None

    skills = [us.skill.name for us in profile.user.skills if us.skill]

    # Resolve target role from active roadmap
    target_role_id = ""
    target_role_title = ""
    if profile.user.roadmaps:
        active_rm = profile.user.roadmaps[0]
        if active_rm.role:
            target_role_id = active_rm.role.slug
            target_role_title = active_rm.role.title

    return ProfileData(
        id=str(profile.id),
        name=profile.full_name or "",
        education=profile.education,
        skills=skills,
        targetRoleId=target_role_id,
        targetRoleTitle=target_role_title,
        createdAt=profile.created_at.isoformat().replace("+00:00", "Z"),
    )
