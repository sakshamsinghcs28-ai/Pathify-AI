from .health import router as health_router
from .roles import router as roles_router
from .skill_gap import router as skill_gap_router
from .profiles import router as profiles_router

__all__ = [
    "health_router",
    "roles_router",
    "skill_gap_router",
    "profiles_router",
]
