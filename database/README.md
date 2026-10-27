# Pathify-AI Database Module

PostgreSQL + SQLAlchemy 2.x async + Alembic starter module.

## Requirements
- Python 3.11+
- PostgreSQL 15+
- Install dependencies from `requirements.txt`

## Setup
1. Create a PostgreSQL database named `pathify_db`.
2. Copy `.env.example` to `.env` and set `DATABASE_URL`.
3. Install dependencies: `pip install -r requirements.txt`
4. From the repository root, run migrations:
   `alembic -c database/alembic.ini upgrade head`

The database package is designed to be imported by the FastAPI backend. Confirm the import path with the backend developer before integration.
