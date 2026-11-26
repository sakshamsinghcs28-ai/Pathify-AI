import uuid
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from database.models import User, UserProfile, UserSkill, Skill, Roadmap, CareerRole
from backend.app.schemas.profiles import ProfileCreateRequest, ProfileData
from backend.app.services.role_service import get_role_by_id_or_slug


async def create_student_profile(
    session: AsyncSession,
    data: ProfileCreateRequest,
    current_user: Optional[User] = None,
) -> ProfileData:
    """Create or update a student profile, linked skills, and target role roadmap in PostgreSQL.

    If current_user is provided, attaches directly to that registered user.
    Otherwise, generates a guest student record for temporary unauthenticated sessions.
    """
    role = await get_role_by_id_or_slug(session, data.targetRoleId)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target role '{data.targetRoleId}' not found",
        )

    if current_user:
        target_user = current_user
        # Find existing profile if any
        res = await session.execute(
            select(UserProfile).where(UserProfile.user_id == target_user.id)
        )
        profile = res.scalar_one_or_none()
        if profile:
            profile.full_name = data.name.strip()
            if data.education:
                profile.education = data.education.strip()
        else:
            profile = UserProfile(
                user_id=target_user.id,
                full_name=data.name.strip(),
                education=data.education.strip() if data.education else None,
            )
            session.add(profile)
        await session.flush()
    else:
        existing_profile = None
        if data.profileId:
            try:
                p_uuid = uuid.UUID(data.profileId)
                res = await session.execute(
                    select(UserProfile).where(UserProfile.id == p_uuid)
                )
                existing_profile = res.scalar_one_or_none()
            except (ValueError, TypeError):
                existing_profile = None

        if existing_profile and existing_profile.user_id:
            profile = existing_profile
            target_user = await session.get(User, profile.user_id)
            profile.full_name = data.name.strip()
            if data.education:
                profile.education = data.education.strip()
        else:
            # 1. Create guest student User
            synthetic_email = f"student_{uuid.uuid4().hex[:12]}@pathify.local"
            target_user = User(
                email=synthetic_email,
                role="student",
                is_active=True,
            )
            session.add(target_user)
            await session.flush()

            # 2. Create UserProfile
            profile = UserProfile(
                user_id=target_user.id,
                full_name=data.name.strip(),
                education=data.education.strip() if data.education else None,
            )
            session.add(profile)
            await session.flush()

    # 3. Create or update active Roadmap for this specific career role
    rm_query = select(Roadmap).where(
        (Roadmap.user_id == target_user.id) & (Roadmap.role_id == role.id)
    )
    rm_res = await session.execute(rm_query)
    roadmap = rm_res.scalar_one_or_none()
    if not roadmap:
        roadmap = Roadmap(
            user_id=target_user.id,
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

        # Remove existing user skills to prevent unique constraint conflicts
        await session.execute(
            delete(UserSkill).where(UserSkill.user_id == target_user.id)
        )

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
                user_id=target_user.id,
                skill_id=sk.id,
                proficiency_level=3,
                verified=False,
            )
            session.add(user_skill)
            saved_skill_names.append(sk.name)

    await session.commit()
    await session.refresh(profile)

    return ProfileData(
        id=str(profile.id),
        userId=str(target_user.id),
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
        userId=str(profile.user_id),
        name=profile.full_name or "",
        education=profile.education,
        skills=skills,
        targetRoleId=target_role_id,
        targetRoleTitle=target_role_title,
        createdAt=profile.created_at.isoformat().replace("+00:00", "Z"),
    )


async def get_profile_by_user_id(
    session: AsyncSession, user_id: uuid.UUID
) -> Optional[ProfileData]:
    """Fetch profile data for a specific user UUID."""
    query = (
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
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

    target_role_id = ""
    target_role_title = ""
    if profile.user.roadmaps:
        active_rm = profile.user.roadmaps[0]
        if active_rm.role:
            target_role_id = active_rm.role.slug
            target_role_title = active_rm.role.title

    return ProfileData(
        id=str(profile.id),
        userId=str(profile.user_id),
        name=profile.full_name or "",
        education=profile.education,
        skills=skills,
        targetRoleId=target_role_id,
        targetRoleTitle=target_role_title,
        createdAt=profile.created_at.isoformat().replace("+00:00", "Z"),
    )
