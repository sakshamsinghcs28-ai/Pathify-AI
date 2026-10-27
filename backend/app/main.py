from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import engine
from backend.app.config import app_settings
from backend.app.routers import (
    health_router,
    roles_router,
    skill_gap_router,
    profiles_router,
)


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

# CORS middleware for seamless frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health_router)
app.include_router(roles_router)
app.include_router(skill_gap_router)
app.include_router(profiles_router)


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=app_settings.host,
        port=app_settings.port,
        reload=app_settings.debug,
    )
