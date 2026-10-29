import os
import re
from typing import List, Tuple
from dotenv import dotenv_values
import httpx

from backend.app.schemas.chat import ChatMessage, ChatResponse


def get_api_key(key_name: str) -> str:
    """Safely check environment or .env for API keys."""
    val = os.getenv(key_name)
    if val:
        return val.strip()
    file_vals = dotenv_values(".env")
    return file_vals.get(key_name, "").strip()


async def ask_gemini(api_key: str, prompt: str, history: List[ChatMessage]) -> str:
    """Query Gemini 1.5 Flash via REST API if configured."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    contents = []
    # Add system context
    system_instruction = (
        "You are Pathify-AI, an expert AI Career Mentor and Industry Skill Mapping Coach. "
        "Provide direct, inspiring, and actionable career advice for Full-Stack Developers, "
        "Data Analysts, and AI Engineers. Focus on skill milestones, practical projects, and learning roadmaps."
    )
    for h in history[-4:]:
        role = "user" if h.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h.content}]})

    contents.append({"role": "user", "parts": [{"text": f"{system_instruction}\n\nUser Question: {prompt}"}]})

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, json={"contents": contents})
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"]
        raise RuntimeError(f"Gemini API returned status {res.status_code}")


def rule_based_career_advisor(query: str, context_role_id: str | None = None) -> Tuple[str, List[str]]:
    """Comprehensive, intelligent domain fallback for career roadmap advice."""
    q = query.lower().strip()

    # Suggestions pool
    default_suggestions = [
        "What are the core skills for an AI Engineer?",
        "How do I build a portfolio as a Data Analyst?",
        "What is the best roadmap to learn Full-Stack Web Development?",
        "How do I prepare for tech coding interviews?",
    ]

    # 1. Greetings & Meta
    if re.search(r"\b(hello|hi|hey|greetings|start|who are you|what is pathify)\b", q):
        reply = (
            "👋 **Hello! I'm your Pathify-AI Career & Skill Advisor.**\n\n"
            "I'm here to help you navigate your journey into tech careers. Here is what we can do:\n"
            "- **Analyze Skill Gaps**: Compare your current skills against industry requirements.\n"
            "- **Build Custom Roadmaps**: Get a tailored week-by-week learning plan.\n"
            "- **Target Specific Roles**: Get tailored advice for **Full-Stack Developer**, **Data Analyst**, or **AI Engineer**.\n\n"
            "Which role are you aiming for, or what skill are you currently learning?"
        )
        return reply, [
            "Tell me about Full-Stack Developer",
            "Tell me about Data Analyst",
            "Tell me about AI Engineer",
            "How does the Skill-Gap Analyzer work?",
        ]

    # 2. AI Engineer Queries
    if "ai" in q or "artificial intelligence" in q or "machine learning" in q or "deep learning" in q or "llm" in q or "pytorch" in q:
        reply = (
            "🤖 **AI Engineer Career Path & Skill Guide**\n\n"
            "An **AI Engineer** designs, fine-tunes, and deploys intelligent models and agents into production environments.\n\n"
            "### Recommended 4-Phase Roadmap:\n"
            "1. **Core Foundations**: Python (NumPy, Vectorization), Linear Algebra, and Calculus basics.\n"
            "2. **Classical Machine Learning**: Scikit-Learn (Classification, Regression, Cross-validation, Hyperparameter tuning).\n"
            "3. **Deep Learning & Transformers**: PyTorch, neural architectures (CNNs, Attention, Transformers), and Hugging Face.\n"
            "4. **Modern GenAI & MLOps**: Vector databases (Chroma, Pinecone), Retrieval-Augmented Generation (RAG), and serving models via **FastAPI** & **Docker**.\n\n"
            "💡 **Standout Portfolio Project Idea**: Build an enterprise knowledge-base search engine using RAG that indexes PDF documentation and provides sourced answers with citation links."
        )
        return reply, [
            "What projects should an AI Engineer build?",
            "What is RAG and why is it important?",
            "How do I switch from Web Development to AI?",
            "What math is required for AI?",
        ]

    # 3. Data Analyst Queries
    if "data" in q or "analyst" in q or "sql" in q or "tableau" in q or "power bi" in q or "pandas" in q or "excel" in q:
        reply = (
            "📊 **Data Analyst Career Path & Skill Guide**\n\n"
            "A **Data Analyst** turns raw numbers into strategic business insights using querying, statistical modeling, and visual storytelling.\n\n"
            "### Key Skill Priorities:\n"
            "1. **Advanced SQL** *(Most Crucial)*: Joins, Window functions (`ROW_NUMBER`, `LEAD/LAG`), CTEs, and aggregation.\n"
            "2. **Spreadsheet Modeling**: Advanced Excel / Google Sheets (`XLOOKUP`, Pivot Tables, conditional forecasting).\n"
            "3. **Python for Analytics**: Pandas for data cleansing, NumPy for computations, and Seaborn/Matplotlib for exploratory plots.\n"
            "4. **Business Intelligence (BI)**: Power BI or Tableau to create dynamic, stakeholder-ready dashboards.\n\n"
            "💡 **Standout Portfolio Project Idea**: Analyze an e-commerce or churn dataset. Clean the data with Pandas, model it with SQL, and build a dynamic dashboard showing Customer Lifetime Value (CLV) and churn drivers."
        )
        return reply, [
            "What are the most asked SQL interview questions?",
            "Power BI vs Tableau: Which should I learn?",
            "How do I build a Data Analyst portfolio without experience?",
            "What is the difference between Data Analyst and Data Scientist?",
        ]

    # 4. Full-Stack Developer Queries
    if "full-stack" in q or "full stack" in q or "frontend" in q or "backend" in q or "web dev" in q or "react" in q or "node" in q:
        reply = (
            "💻 **Full-Stack Developer Career Path & Skill Guide**\n\n"
            "A **Full-Stack Developer** bridges user experience with resilient backend infrastructure and database modeling.\n\n"
            "### Recommended Modern Tech Stack:\n"
            "- **Frontend**: HTML5, Modern CSS (Tailwind CSS, Flexbox/Grid), JavaScript (ES6+), and React.\n"
            "- **Backend**: Node.js + Express.js or Python + FastAPI.\n"
            "- **Databases**: PostgreSQL (Relational) and MongoDB (Document/NoSQL).\n"
            "- **DevOps & Tooling**: Git & GitHub, Docker containers, and CI/CD pipelines.\n\n"
            "💡 **Standout Portfolio Project Idea**: Build a collaborative SaaS application (like a real-time task manager or markdown workspace) with user authentication, database migrations, and responsive UI."
        )
        return reply, [
            "What backend framework is best: FastAPI or Express?",
            "How do I learn React efficiently?",
            "What makes a Full-Stack portfolio project stand out?",
            "SQL vs NoSQL: When should I use which?",
        ]

    # 5. Project Ideas & Portfolio Advice
    if "project" in q or "portfolio" in q or "resume" in q or "github" in q:
        reply = (
            "🚀 **How to Build a High-Impact Tech Portfolio**\n\n"
            "Recruiters look for depth, problem-solving, and clean deployment over dozens of tutorial clones:\n\n"
            "1. **Depth over Quantity**: 2–3 polished, deployed full-stack or analytical projects are far better than 10 simple clones.\n"
            "2. **Provide Live Demos**: Always host your application (e.g. Render, Vercel, Supabase, Hugging Face) and include a direct link in your GitHub README.\n"
            "3. **Document Architecture**: Write a comprehensive `README.md` detailing architecture, database schema diagrams, setup steps, and lessons learned.\n"
            "4. **Solve Real Problems**: Build tools that real people or organizations could use (e.g. an AI resume reviewer, a local market pricing tracker, or a roadmap engine!)."
        )
        return reply, [
            "Give me 3 project ideas for Full-Stack",
            "Give me 3 project ideas for AI Engineer",
            "Give me 3 project ideas for Data Analyst",
        ]

    # 6. Interview Preparation
    if "interview" in q or "hired" in q or "job" in q or "salary" in q or "prep" in q:
        reply = (
            "🎯 **Technical Interview Success Framework**\n\n"
            "Tech interviews typically evaluate three dimensions:\n"
            "1. **Fundamentals & Coding**: Practice core DSA (Arrays, Hash Maps, Two Pointers, Trees) and SQL joins.\n"
            "2. **System & Architecture Design**: Be able to explain how your portfolio projects handle data flow, database relationships, error handling, and API security.\n"
            "3. **Behavioral & Communication**: Use the **STAR method** (Situation, Task, Action, Result) to describe challenges, debugging sessions, and teamwork."
        )
        return reply, [
            "How to answer: Tell me about a difficult bug you solved",
            "What questions should I ask the interviewer?",
            "How should I structure my tech resume?",
        ]

    # Default fallback
    reply = (
        f"💡 **Career Guidance for: *\"{query}\"***\n\n"
        "Here are key recommendations from the Pathify-AI Career Engine:\n\n"
        "1. **Identify Target Outcomes**: Pick one clear role (Full-Stack Developer, Data Analyst, or AI Engineer) to avoid tutorial fatigue.\n"
        "2. **Run a Skill-Gap Analysis**: Head to our **Skill Gap Analyzer** tab to check which industry-standard skills you have and which are missing.\n"
        "3. **Follow a Structured Roadmap**: Spend 70% of your study time building practical code and 30% reviewing documentation.\n\n"
        "Ask me about any specific skill (like Python, React, SQL, PyTorch, Docker) or career path for customized guidance!"
    )
    return reply, default_suggestions


async def process_chat_message(
    message: str, history: List[ChatMessage], context_role_id: str | None = None
) -> ChatResponse:
    """Processes user chat message with real AI or rule-based expert mode."""
    gemini_key = get_api_key("GEMINI_API_KEY")
    if gemini_key:
        try:
            reply = await ask_gemini(gemini_key, message, history)
            return ChatResponse(
                reply=reply,
                suggestedQuestions=[
                    "What are the highest-paying skills in this field?",
                    "What learning resources do you recommend?",
                    "Give me a step-by-step 30-day study plan",
                ],
                mode="ai_model",
                modelName="Gemini 1.5 Flash",
            )
        except Exception:
            # Fall back gracefully to rule-based engine if API fails
            pass

    reply, suggestions = rule_based_career_advisor(message, context_role_id)
    return ChatResponse(
        reply=reply,
        suggestedQuestions=suggestions,
        mode="expert_rules",
        modelName="Pathify Career Intelligence Engine (Expert Mode)",
    )
