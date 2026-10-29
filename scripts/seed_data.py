"""Database seed script for Pathify-AI.

Populates initial sample career roles, required skills, and learning roadmap templates
matching the contracts in API.md and prototype requirements:
1. Full-Stack Developer
2. Data Analyst
3. AI Engineer
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
        "title": "Full-Stack Developer",
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
        "title": "Data Analyst",
        "industry": "Data & Analytics",
        "description": "Transforms raw enterprise data into actionable insights, dashboards, and executive reports.",
        "skills": [
            ("SQL & Relational Databases", "Master SQL queries, window functions, multi-table joins, and data aggregations.", "Write analytical queries across complex transactional datasets to calculate retention metrics.", "2-3 weeks"),
            ("Python", "Learn Python fundamentals, data manipulation syntax, and standard libraries.", "Automate data extraction and basic report generation using Python scripts.", "2 weeks"),
            ("Data Cleaning with Pandas", "Clean messy datasets, handle missing values, reshape dataframes, and perform vector calculations.", "Clean and normalize an untidy real-world CSV dataset with thousands of records.", "2 weeks"),
            ("Statistics & Exploratory Data Analysis", "Apply descriptive statistics, hypothesis testing, distributions, and correlation analysis.", "Conduct an in-depth exploratory analysis discovering key correlations in business metrics.", "2 weeks"),
            ("Power BI / Tableau", "Build interactive business intelligence dashboards with dynamic filters and drill-downs.", "Develop an executive sales and customer cohort retention dashboard.", "1-2 weeks"),
            ("Excel & Spreadsheets", "Master Pivot Tables, advanced lookup formulas (XLOOKUP), and data modeling in spreadsheets.", "Build a multi-tab financial forecast model using dynamic formulas and conditional formatting.", "1 week"),
            ("Git & GitHub", "Learn version control workflows, branching strategies, and reproducible analysis notebooks.", "Track analysis notebooks and script versions using Git and GitHub.", "1 week"),
        ],
    },
    {
        "slug": "role-3",
        "title": "AI Engineer",
        "industry": "Artificial Intelligence & ML",
        "description": "Develops, fine-tunes, and deploys intelligent models, LLM agents, and machine learning pipelines into production.",
        "skills": [
            ("Python", "Master Python 3 fundamentals, asynchronous concurrency, and performance optimization.", "Write modular, object-oriented Python packages for ML pipelines.", "2 weeks"),
            ("Machine Learning Algorithms (Scikit-Learn)", "Understand supervised and unsupervised learning, cross-validation, and hyperparameter tuning.", "Train, evaluate, and tune regression and classification models on structured datasets.", "2-3 weeks"),
            ("Deep Learning & PyTorch", "Understand neural network architectures (CNNs, Transformers), loss functions, and backpropagation.", "Build and train a custom neural network using PyTorch with GPU acceleration.", "3-4 weeks"),
            ("Natural Language Processing (NLP) & LLMs", "Learn tokenization, embeddings, prompt engineering, fine-tuning, and transformer attention mechanisms.", "Implement an autonomous agent or text-processing pipeline using modern LLM APIs.", "2-3 weeks"),
            ("Vector Databases & RAG", "Master semantic embeddings, vector indexing (Chroma, Pinecone, FAISS), and Retrieval-Augmented Generation.", "Build a production RAG system that answers questions over custom enterprise documentation.", "2 weeks"),
            ("Model Deployment & FastAPI", "Serve machine learning models via high-throughput, low-latency REST APIs.", "Deploy an ML inference service with Docker, FastAPI, and asynchronous batching.", "1-2 weeks"),
            ("Docker & MLOps Basics", "Containerize inference workloads, monitor model drift, and automate pipelines.", "Containerize an AI service and orchestrate it with Docker Compose.", "1-2 weeks"),
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
                desc = f"Goal: {goal} | Task: {task} | Duration: {duration}"
                if key not in existing_skills:
                    skill_slug = key.replace(" ", "-").replace("&", "and").replace("/", "-")
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
                    skill.description = desc  # update description with goal/task/duration

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
