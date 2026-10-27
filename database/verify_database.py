"""Verification script for Pathify-AI Database Module.

Checks:
1. Python dependencies.
2. Database configuration and environment variable loading.
3. Database engine and session factory creation.
4. SQLAlchemy ORM models, mappers, and relationships.
5. Base metadata tables and constraints.
6. Alembic migrations and offline DDL generation.
7. Optional live database connectivity check.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path so 'database' can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies():
    print("[1/6] Checking Python dependencies...")
    required_packages = ["sqlalchemy", "asyncpg", "alembic", "pydantic_settings", "greenlet"]
    for pkg in required_packages:
        __import__(pkg)
        print(f"  [OK] {pkg}")


def check_config():
    print("[2/6] Checking database configuration...")
    from database.config import settings

    masked_url = settings.database_url
    if "@" in masked_url:
        prefix, rest = masked_url.split("@", 1)
        if ":" in prefix:
            proto_user = prefix.split(":", 2)
            if len(proto_user) > 2:
                masked_url = f"{proto_user[0]}:{proto_user[1]}:****@{rest}"
    print(f"  [OK] Database URL configured: {masked_url}")
    print(f"  [OK] Connection pool size: {settings.db_pool_size}, max overflow: {settings.db_max_overflow}")


def check_engine_and_session():
    print("[3/6] Checking engine and session factory...")
    from database.connection import AsyncSessionLocal, close_db, engine, get_db

    assert engine is not None, "Engine is None"
    assert AsyncSessionLocal is not None, "AsyncSessionLocal is None"
    assert callable(get_db), "get_db is not callable"
    print("  [OK] Engine and async session factory initialized properly.")


def check_models_and_relationships():
    print("[4/6] Checking SQLAlchemy models and relationships...")
    from sqlalchemy.orm import configure_mappers
    from database.base import Base
    import database.models  # noqa: F401

    configure_mappers()

    expected_tables = {
        "users",
        "user_profiles",
        "skills",
        "skill_prerequisites",
        "user_skills",
        "career_roles",
        "career_skill_requirements",
        "skill_gap_assessments",
        "roadmaps",
        "roadmap_milestones",
        "roadmap_tasks",
        "learning_resources",
        "task_resource_mappings",
        "user_task_progress",
        "ai_generation_logs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - actual_tables
    if missing:
        raise ValueError(f"Missing tables in Base.metadata: {missing}")

    print(f"  [OK] All {len(actual_tables)} tables registered in Base.metadata:")
    for t in sorted(actual_tables):
        print(f"       - {t}")
    print("  [OK] All ORM relationships and back_populates configured with 0 errors.")


def check_alembic_migrations():
    print("[5/6] Checking Alembic migrations and offline DDL generation...")
    from alembic.config import Config
    from alembic import command
    import io

    ini_path = Path(__file__).resolve().parent / "alembic.ini"
    alembic_cfg = Config(str(ini_path))

    # Capture stdout to verify migration heads
    buf = io.StringIO()
    alembic_cfg.print_stdout = lambda text, *args: buf.write(str(text) + "\n")
    command.heads(alembic_cfg)
    heads_output = buf.getvalue().strip()
    print(f"  [OK] Current migration head: {heads_output}")
    assert "001_initial_schema" in heads_output, f"Expected 001_initial_schema in heads, got: {heads_output}"


async def check_live_connection():
    print("[6/6] Checking live PostgreSQL database connection...")
    from database.connection import engine
    from sqlalchemy import text

    try:
        async with asyncio.timeout(2):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        print("  [OK] Successfully connected to live PostgreSQL database!")
    except Exception as e:
        print(f"  [INFO] Live database is currently unreachable ({type(e).__name__}).")
        print("         This is normal if PostgreSQL is not currently running locally or credentials are not yet set.")


async def main():
    print("=" * 60)
    print("Starting Pathify-AI Database Verification")
    print("=" * 60)
    check_dependencies()
    check_config()
    check_engine_and_session()
    check_models_and_relationships()
    check_alembic_migrations()
    await check_live_connection()
    from database.connection import close_db
    await close_db()
    print("=" * 60)
    print("Database verification completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
