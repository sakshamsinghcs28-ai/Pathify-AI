# Pathify-AI
AI-powered career roadmap and industry skill mapping platform that helps students identify skill gaps and plan their career development.

AI Career Roadmap and Industry Skill Mapping Engine.

## Tech Stack
- **Frontend**: Responsive Single-Page Application (HTML5, Tailwind CSS, Lucide Icons) served seamlessly on `http://localhost:5000`
- **Backend**: FastAPI (Python 3.11+) + Uvicorn
- **Database**: PostgreSQL 15+ + SQLAlchemy 2.x Async + asyncpg
- **Migrations & Seeding**: Alembic + automated reference data seeding

---

## Quick Start (Demo Prototype)

### 1. Environment Setup
Verify your `.env` has your PostgreSQL connection string:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pathify_db
# Optional: Add GEMINI_API_KEY=your_key to activate Gemini LLM in the chatbot
```

### 2. Run Database Migrations & Seed Data
```bash
# Run migrations (already applied)
.\.venv\Scripts\alembic -c database/alembic.ini upgrade head

# Seed primary career roles (Full-Stack Developer, Data Analyst, AI Engineer)
.\.venv\Scripts\python scripts/seed_data.py
```

### 3. Launch Pathify-AI Application
Run the single command below to launch both the frontend dashboard and backend API:
```bash
.\.venv\Scripts\uvicorn backend.app.main:app --host 0.0.0.0 --port 5000 --reload
```

Open your browser to:
👉 **http://localhost:5000**

---

## Prototype Features Available in the Demo

1. **Modern Dashboard**: High-level platform statistics, career overviews, and quick action navigators.
2. **Career Selection Explorer**: Deep-dive into 3 industry career pathways:
   - **Full-Stack Developer** (Software Development)
   - **Data Analyst** (Data & Analytics)
   - **AI Engineer** (Artificial Intelligence & ML)
3. **Skill-Gap Analyzer**:
   - Interactive skill checklist toggle + custom skill input.
   - Real-time comparison calculating match percentage, matched skills, and missing skills against live PostgreSQL data.
4. **Learning Roadmap Generator**:
   - Step-by-step milestones dynamically generated from missing skills.
   - Shows learning goals, practical hands-on tasks, and estimated durations.
   - Interactive checklist allowing demonstration of milestone completion.
   - "Save Student Profile" modal to persist student profiles to PostgreSQL `pathify_db`.
5. **AI Career Mentor Chatbot**:
   - Interactive real-time conversation interface with suggested quick-prompt chips.
   - Real Gemini LLM mode if `GEMINI_API_KEY` is provided in `.env`.
   - Comprehensive, rule-based expert career engine fallback covering tech roles, portfolio advice, roadmaps, and interview tips.

---

## Running Automated Verification Tests
```bash
.\.venv\Scripts\python backend/tests/test_api_endpoints.py
```
Validates the frontend static serving, all 7 API endpoints, and the AI chatbot.

Interactive Swagger API docs are available at `http://localhost:5000/docs`.
