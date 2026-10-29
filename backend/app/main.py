from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from database import engine
from backend.app.config import app_settings
from backend.app.routers import (
    health_router,
    roles_router,
    skill_gap_router,
    profiles_router,
    chat_router,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    yield
    # Shutdown actions
    await engine.dispose()


app = FastAPI(
    title=app_settings.app_name,
    description="AI Career Roadmap and Industry Skill Mapping Engine Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for seamless integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers first so /api/* routes take precedence
app.include_router(health_router)
app.include_router(roles_router)
app.include_router(skill_gap_router)
app.include_router(profiles_router)
app.include_router(chat_router)

# Mount Frontend static files at root if directory exists
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=app_settings.host,
        port=app_settings.port,
        reload=app_settings.debug,
    )
