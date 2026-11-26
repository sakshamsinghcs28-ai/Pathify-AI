import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, UserProfile, PasswordResetToken
from backend.app.config import app_settings
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from backend.app.services.email_service import send_password_reset_email


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify a plain password against the stored bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=app_settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(
        to_encode,
        app_settings.jwt_secret_key,
        algorithm=app_settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            app_settings.jwt_secret_key,
            algorithms=[app_settings.jwt_algorithm],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def user_to_response(user: User) -> UserResponse:
    """Convert a User ORM model to a clean UserResponse Pydantic schema."""
    full_name = user.profile.full_name if user.profile else None
    education = user.profile.education if user.profile else None
    created_at_str = (
        user.created_at.isoformat().replace("+00:00", "Z")
        if user.created_at
        else ""
    )
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        full_name=full_name,
        education=education,
        created_at=created_at_str,
    )


async def register_user(
    session: AsyncSession, data: UserRegisterRequest
) -> TokenResponse:
    """Register a new user with hashed password and initial user profile."""
    # 1. Validate password match if confirm_password provided
    if data.confirm_password and data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    clean_email = data.email.strip().lower()

    # 2. Check if email is already taken
    existing_user_query = select(User).where(func.lower(User.email) == clean_email)
    res = await session.execute(existing_user_query)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # 3. Hash password
    hashed_pw = hash_password(data.password)

    # 4. Create User
    new_user = User(
        email=clean_email,
        hashed_password=hashed_pw,
        role="student",
        is_active=True,
    )
    session.add(new_user)
    await session.flush()

    # 5. Create associated UserProfile
    new_profile = UserProfile(
        user_id=new_user.id,
        full_name=data.full_name.strip(),
    )
    session.add(new_profile)
    await session.commit()
    await session.refresh(new_user, attribute_names=["profile"])

    # 6. Generate access token
    token = create_access_token(
        {
            "sub": str(new_user.id),
            "email": new_user.email,
            "role": new_user.role,
        }
    )

    return TokenResponse(
        success=True,
        message="Registration successful",
        access_token=token,
        token_type="bearer",
        user=user_to_response(new_user),
    )


async def authenticate_user(
    session: AsyncSession, data: UserLoginRequest
) -> TokenResponse:
    """Authenticate existing user credentials and return a signed JWT."""
    clean_email = data.email.strip().lower()

    # Query user with profile
    query = (
        select(User)
        .where(func.lower(User.email) == clean_email)
        .options(selectinload(User.profile))
    )
    res = await session.execute(query)
    user = res.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive. Please contact support.",
        )

    # Generate token
    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return TokenResponse(
        success=True,
        message="Login successful",
        access_token=token,
        token_type="bearer",
        user=user_to_response(user),
    )


async def get_user_by_id(
    session: AsyncSession, user_id_val: uuid.UUID | str
) -> Optional[User]:
    """Retrieve user with profile by UUID."""
    if isinstance(user_id_val, str):
        try:
            uid = uuid.UUID(user_id_val)
        except (ValueError, TypeError):
            return None
    else:
        uid = user_id_val

    query = (
        select(User)
        .where(User.id == uid)
        .options(selectinload(User.profile))
    )
    res = await session.execute(query)
    return res.scalar_one_or_none()


def generate_reset_token() -> tuple[str, str]:
    """Generate a cryptographically secure random token and its SHA-256 hash."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure database lookup."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def resolve_frontend_base_url(
    origin: Optional[str] = None,
    referer: Optional[str] = None,
    request_base_url: Optional[str] = None,
) -> str:
    """Resolve a valid, absolute HTTP(S) base URL for frontend links.

    Strictly guarantees that 'null', 'None', 'undefined', or non-HTTP values are NEVER used.
    Evaluation order:
    1. Valid HTTP/HTTPS origin (e.g. from Request Origin header, if not 'null').
    2. Valid HTTP/HTTPS referer (extracting scheme + host:port).
    3. Configured app_settings.frontend_url from .env (e.g. http://localhost:5000).
    4. request_base_url from FastAPI (if starts with http/https).
    5. Final fallback: 'http://localhost:5000'.
    """
    def is_valid_http(val: Optional[str]) -> bool:
        if not val or not isinstance(val, str):
            return False
        cleaned = val.strip().lower()
        if cleaned in ("null", "none", "undefined", "", "false", "0"):
            return False
        return cleaned.startswith("http://") or cleaned.startswith("https://")

    # 1. Inspect origin
    if is_valid_http(origin):
        return origin.strip().rstrip("/")

    # 2. Inspect referer
    if is_valid_http(referer):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(referer.strip())
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        except Exception:
            pass

    # 3. Inspect configured frontend_url from .env
    if is_valid_http(app_settings.frontend_url):
        return app_settings.frontend_url.strip().rstrip("/")

    # 4. Inspect request_base_url
    if is_valid_http(request_base_url):
        return request_base_url.strip().rstrip("/")

    # 5. Default fallback
    return "http://localhost:5000"


async def request_password_reset(
    session: AsyncSession, email: str, origin: Optional[str] = None
) -> ForgotPasswordResponse:
    """Initiate password recovery by generating a 20-minute single-use token and emailing it via Resend."""
    clean_email = email.strip().lower()

    # Verify user exists in PostgreSQL
    query = select(User).where(func.lower(User.email) == clean_email)
    res = await session.execute(query)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered account was found with this email address.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently inactive. Please contact support.",
        )

    now = datetime.now(timezone.utc)

    # Invalidate any existing unused reset tokens for this user
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Generate new secure token with 20-minute expiry
    raw_token, token_hash = generate_reset_token()
    expires_at = now + timedelta(minutes=app_settings.reset_token_expire_minutes)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(reset_record)
    await session.commit()

    # Construct the reset password URL using guaranteed valid HTTP(S) base URL
    base_url = resolve_frontend_base_url(origin=origin).rstrip("/")
    reset_url = f"{base_url}/reset-password.html?token={raw_token}"

    # Dispatch real email via Resend API
    await send_password_reset_email(to_email=user.email, reset_url=reset_url)

    return ForgotPasswordResponse(
        success=True,
        message=f"A password reset link has been dispatched to your email address ({user.email}). Please check your inbox.",
    )


async def verify_reset_token(session: AsyncSession, token: str) -> PasswordResetToken:
    """Validate that a reset token exists, has not been used, and has not expired."""
    clean_token = token.strip()
    if not clean_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token is required.",
        )

    token_hash = hash_token(clean_token)
    query = (
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .options(selectinload(PasswordResetToken.user))
    )
    res = await session.execute(query)
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unrecognized password reset token.",
        )

    if token_record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has already been used. Please request a new one.",
        )

    now = datetime.now(timezone.utc)
    if now > token_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired (20-minute limit). Please request a new one.",
        )

    return token_record


async def reset_password_with_token(
    session: AsyncSession, data: ResetPasswordRequest
) -> ResetPasswordResponse:
    """Verify single-use token and update user password securely with bcrypt."""
    if data.confirm_password and data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters in length.",
        )

    token_record = await verify_reset_token(session, data.token)
    user = token_record.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated user account was not found.",
        )

    # 1. Verify whether the new password matches the user's current password
    if verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot reuse your current password. Please choose a different password.",
        )

    # Hash new password with bcrypt
    user.hashed_password = hash_password(data.password)

    # Invalidate token so it cannot be used again
    token_record.used_at = datetime.now(timezone.utc)

    await session.commit()

    return ResetPasswordResponse(
        success=True,
        message="Your password has been successfully reset. You can now log in with your new password.",
    )
