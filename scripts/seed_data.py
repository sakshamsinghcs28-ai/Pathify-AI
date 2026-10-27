"""Database seed script for Pathify-AI.

Populates initial sample career roles, required skills, and learning roadmap templates
matching the contracts in API.md.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from database import AsyncSessionLocal, engine
from database.models import CareerRole, Skill, CareerSkillRequirement, LearningResource


ROLES_DATA = [
    {
        "slug": "role-1",
        "title": "Full-Stack Web Developer",
        "industry": "Software Development",
        "description": "Builds both user-facing frontends and backend servers/APIs for modern web applications.",
        "skills": [
            ("JavaScript", "Master ES6+ JavaScript syntax, asynchronous patterns, and modern DOM APIs.", "Build an interactive client-side application with dynamic state management.", "1-2 weeks"),
            ("HTML & CSS", "Master semantic HTML markup, responsive web design with Flexbox and CSS Grid.", "Build a responsive multi-page personal portfolio site from scratch without frameworks.", "1-2 weeks"),
            ("React", "Learn component lifecycle, hooks, context API, and single-page application routing.", "Develop a full-featured dashboard with client-side state and component reusability.", "2-3 weeks"),
            ("Node.js", "Understand event loop, asynchronous I/O, Node core modules, and npm ecosystem.", "Build command-line utilities and basic HTTP servers using core modules.", "1-2 weeks"),
            ("Express.js", "Create robust RESTful APIs, middleware chains, error handling, and security best practices.", "Implement a RESTful API with validation, routing, and centralized error handling.", "2-3 weeks"),
            ("MongoDB", "Design document schemas, implement CRUD operations, aggregation pipelines, and indexing.", "Integrate NoSQL persistence into a REST API with indexing and pagination.", "1-2 weeks"),
            ("Git & GitHub", "Learn version control workflows, branching strategies, merge conflicts, and pull requests.", "Manage code repositories using feature branches, pull requests, and commit hygiene.", "1 week"),
        ],
    },
    {
        "slug": "role-2",
        "title": "Frontend Specialist",
        "industry": "Software Development",
        "description": "Specializes in building responsive, accessible, and high-performance user interfaces.",
        "skills": [
            ("HTML & CSS", "Master semantic HTML markup, responsive web design with Flexbox and CSS Grid.", "Build a responsive multi-page personal portfolio site from scratch without frameworks.", "1-2 weeks"),
            ("JavaScript", "Master ES6+ JavaScript syntax, asynchronous patterns, and modern DOM APIs.", "Build an interactive client-side application with dynamic state management.", "1-2 weeks"),
            ("TypeScript", "Apply static typing, interfaces, generics, and strict TypeScript compiler settings.", "Refactor a JavaScript project to TypeScript with zero compiler errors.", "2 weeks"),
            ("React", "Learn component lifecycle, hooks, context API, and single-page application routing.", "Develop a full-featured dashboard with client-side state and component reusability.", "2-3 weeks"),
            ("Tailwind CSS", "Build responsive modern interfaces using utility-first CSS and component abstractions.", "Design a mobile-first responsive landing page with dark mode support.", "1 week"),
            ("Git & GitHub", "Learn version control workflows, branching strategies, merge conflicts, and pull requests.", "Manage code repositories using feature branches, pull requests, and commit hygiene.", "1 week"),
        ],
    },
    {
        "slug": "role-3",
        "title": "Backend & Cloud Engineer",
        "industry": "Software Development",
        "description": "Architects scalable APIs, database schemas, and cloud deployment pipelines.",
        "skills": [
            ("Python", "Master Python 3 fundamentals, data structures, OOP, and asynchronous programming.", "Write modular Python packages with type annotations and unit tests.", "2 weeks"),
            ("SQL & Relational Databases", "Master relational modeling, ACID transactions, complex joins, and query optimization.", "Design and optimize a normalized relational schema with indexing.", "2 weeks"),
            ("Docker", "Containerize services, create multi-stage builds, and manage local multi-container setups.", "Containerize backend services with Docker Compose for local development.", "1-2 weeks"),
            ("AWS / Cloud Basics", "Understand cloud computing models, virtual servers, managed databases, and IAM.", "Deploy a containerized API on a cloud provider with environment secrets.", "2-3 weeks"),
            ("Git & GitHub", "Learn version control workflows, branching strategies, merge conflicts, and pull requests.", "Manage code repositories using feature branches, pull requests, and commit hygiene.", "1 week"),
        ],
    },
]


async def seed():
    print("Seeding database with reference career roles and skills...")
    async with AsyncSessionLocal() as session:
        # Cache existing skills by name
        skills_res = await session.execute(select(Skill))
        existing_skills = {s.name.lower(): s for s in skills_res.scalars().all()}

        # Cache existing roles by slug
        roles_res = await session.execute(select(CareerRole))
        existing_roles = {r.slug: r for r in roles_res.scalars().all()}

        for role_spec in ROLES_DATA:
            slug = role_spec["slug"]
            if slug in existing_roles:
                role = existing_roles[slug]
                role.title = role_spec["title"]
                role.industry = role_spec["industry"]
                role.description = role_spec["description"]
            else:
                role = CareerRole(
                    slug=slug,
                    title=role_spec["title"],
                    industry=role_spec["industry"],
                    description=role_spec["description"],
                )
                session.add(role)
                await session.flush()
                existing_roles[slug] = role

            # Ensure all skills exist
            for skill_name, goal, task, duration in role_spec["skills"]:
                key = skill_name.lower()
                if key not in existing_skills:
                    skill_slug = key.replace(" ", "-").replace("&", "and").replace("/", "-")
                    desc = f"Goal: {goal} | Task: {task} | Duration: {duration}"
                    skill = Skill(
                        slug=skill_slug,
                        name=skill_name,
                        category="technical",
                        description=desc,
                    )
                    session.add(skill)
                    await session.flush()
                    existing_skills[key] = skill
                else:
                    skill = existing_skills[key]

                # Ensure requirement mapping exists
                req_res = await session.execute(
                    select(CareerSkillRequirement).where(
                        CareerSkillRequirement.role_id == role.id,
                        CareerSkillRequirement.skill_id == skill.id,
                    )
                )
                if not req_res.scalar_one_or_none():
                    req = CareerSkillRequirement(
                        role_id=role.id,
                        skill_id=skill.id,
                        required_level=3,
                        importance="required",
                    )
                    session.add(req)

        await session.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
