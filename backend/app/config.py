import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("pathify.config")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    app_name: str = "Pathify-AI Backend API"
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    environment: str = "development"

    # CORS configuration
    cors_origins: list[str] = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    cors_origin_regex: Optional[str] = r"^https://.*\.onrender\.com$"

    # Authentication & JWT Settings (No hardcoded fallback secret)
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Resend Email & Password Reset Settings
    resend_api_key: str = ""
    resend_from_email: str = "Pathify AI <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:5000"
    reset_token_expire_minutes: int = 20

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def validate_jwt_secret_key(cls, v: Optional[str]) -> str:
        insecure_keys = {
            "pathify-ai-secret-key-prod-2026-supersecure",
            "change-this-to-a-long-random-secret-key-for-production-min-32-chars",
            "secret",
            "changeme",
            "your-secret-key",
            "your_jwt_secret_here",
        }
        val = (v or "").strip()
        env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
        is_prod = env in ("production", "prod") or bool(os.getenv("RENDER"))

        # In production, strictly reject missing or known hardcoded fallback keys
        if is_prod:
            if not val or val in insecure_keys or len(val) < 32:
                raise ValueError(
                    "CRITICAL PRODUCTION SECURITY ERROR: JWT_SECRET_KEY is missing, too short (< 32 chars), "
                    "or using an insecure default fallback. You must set a high-entropy JWT_SECRET_KEY in production."
                )
            return val

        # In development: use configured key if valid
        if val and val not in insecure_keys:
            return val

        # If missing or insecure placeholder in local development:
        logger.warning(
            "Security Notice: No secure JWT_SECRET_KEY configured in environment or .env. "
            "Using an auto-generated cryptographically secure 256-bit key for this session."
        )
        return secrets.token_hex(32)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        default_origins = [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
        ]
        origins_set = set(default_origins)

        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        v = parsed
                except Exception:
                    pass
            if isinstance(v, str):
                v = [part.strip() for part in v.split(",") if part.strip()]

        if isinstance(v, (list, set, tuple)):
            for origin in v:
                clean = str(origin).strip().rstrip("/")
                # Never allow wildcard '*' when credentials are used
                if clean and clean != "*":
                    origins_set.add(clean)

        return list(origins_set)

    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR / ".env"),
            str(BACKEND_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


app_settings = AppSettings()

# Ensure frontend_url is always included in cors_origins if configured
if app_settings.frontend_url:
    clean_fe = app_settings.frontend_url.strip().rstrip("/")
    if clean_fe and clean_fe not in app_settings.cors_origins:
        app_settings.cors_origins.append(clean_fe)
