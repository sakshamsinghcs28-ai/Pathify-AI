import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

logger = logging.getLogger("pathify.api")

from database import engine
from backend.app.config import app_settings
from backend.app.routers import (
    health_router,
    roles_router,
    skill_gap_router,
    profiles_router,
    chat_router,
    auth_router,
    resume_router,
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

# Secure CORS configuration: Explicit origins without wildcard credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_origin_regex=app_settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Global exception handler ensuring all uncaught errors return JSON
# In production, prevents internal exception or database traces from leaking to users
@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing {request.method} {request.url.path}: {exc}")
    detail_msg = (
        f"An unexpected server error occurred: {str(exc)}"
        if app_settings.debug
        else "An internal server error occurred. Please try again later."
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail_msg,
            "success": False,
        },
    )

# Mount API routers first so /api/* routes take precedence
app.include_router(health_router)
app.include_router(roles_router)
app.include_router(skill_gap_router)
app.include_router(profiles_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(resume_router)


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page():
    reset_file = FRONTEND_DIR / "reset-password.html"
    if reset_file.exists():
        return FileResponse(str(reset_file))
    return {"error": "Page not found"}


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
