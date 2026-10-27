# Pathify-AI
AI-powered career roadmap and industry skill mapping platform that helps students identify skill gaps and plan their career development.

AI Career Roadmap and Industry Skill Mapping Engine.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+) + Uvicorn
- **Database**: PostgreSQL 15+ + SQLAlchemy 2.x Async + asyncpg
- **Migrations**: Alembic

## Getting Started

### 1. Environment Setup
Create or verify `.env` in the project root or in `database/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pathify_db
```

### 2. Install Dependencies
```bash
python -m venv .venv
.\.venv\Scripts\pip install -r database/requirements.txt
.\.venv\Scripts\pip install -r backend/requirements.txt
```

### 3. Database Migrations & Seeding
```bash
# Run Alembic migrations
.\.venv\Scripts\alembic -c database/alembic.ini upgrade head

# Seed initial reference career roles and skills
.\.venv\Scripts\python scripts/seed_data.py
```

### 4. Run the Backend API
Start the server at `http://localhost:5000`:
```bash
.\.venv\Scripts\uvicorn backend.app.main:app --host 0.0.0.0 --port 5000 --reload
```
Or with npm if installed:
```bash
npm start
```

### 5. Run Integration Tests
```bash
.\.venv\Scripts\python backend/tests/test_api_endpoints.py
```

API documentation and contract definitions are in [API.md](API.md).
Interactive Swagger UI is available at `http://localhost:5000/docs`.
