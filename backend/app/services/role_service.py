from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CareerRole, CareerSkillRequirement, Skill
from backend.app.schemas.roles import RoleItem, RolesResponse


async def get_role_by_id_or_slug(session: AsyncSession, identifier: str) -> Optional[CareerRole]:
    """Find a role by slug (e.g. 'role-1') or UUID."""
    # First try by slug
    query = (
        select(CareerRole)
        .where(CareerRole.slug == identifier)
        .options(
            selectinload(CareerRole.skill_requirements).joinedload(CareerSkillRequirement.skill)
        )
    )
    res = await session.execute(query)
    role = res.scalar_one_or_none()
    if role:
        return role

    # Next try by UUID if valid UUID string
    try:
        val_uuid = uuid.UUID(identifier)
        query = (
            select(CareerRole)
            .where(CareerRole.id == val_uuid)
            .options(
                selectinload(CareerRole.skill_requirements).joinedload(CareerSkillRequirement.skill)
            )
        )
        res = await session.execute(query)
        return res.scalar_one_or_none()
    except (ValueError, TypeError):
        pass

    return None


async def get_all_roles(session: AsyncSession) -> RolesResponse:
    """Retrieve all roles with their required skills."""
    query = (
        select(CareerRole)
        .order_by(CareerRole.slug)
        .options(
            selectinload(CareerRole.skill_requirements).joinedload(CareerSkillRequirement.skill)
        )
    )
    res = await session.execute(query)
    roles = res.scalars().all()

    items = []
    for r in roles:
        skills = [req.skill.name for req in r.skill_requirements if req.skill]
        items.append(
            RoleItem(
                id=r.slug,
                title=r.title,
                category=r.industry or "Software Development",
                description=r.description or "",
                requiredSkills=skills,
            )
        )

    return RolesResponse(
        success=True,
        message="Temporary sample career roles (mock data for development)",
        totalRoles=len(items),
        roles=items,
    )
