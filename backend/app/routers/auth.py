from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models import User
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    AuthMeResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyResetTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from backend.app.services.auth_service import (
    register_user,
    authenticate_user,
    user_to_response,
    request_password_reset,
    verify_reset_token,
    reset_password_with_token,
    resolve_frontend_base_url,
)
from backend.app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
async def register(
    payload: UserRegisterRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Register a new student user, initialize profile in PostgreSQL, and set secure auth cookie."""
    token_response = await register_user(session, payload)
    is_secure = request.url.scheme == "https"
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return token_response


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT token",
)
async def login(
    payload: UserLoginRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Verify credentials, return a signed JWT access token, and set secure auth cookie."""
    token_response = await authenticate_user(session, payload)
    is_secure = request.url.scheme == "https"
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return token_response


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out user and clear session cookies",
)
async def logout(response: Response):
    """Clear access_token cookie and invalidate active browser session."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"success": True, "message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=AuthMeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user details",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retrieve current logged in user and profile details from JWT token."""
    return AuthMeResponse(
        success=True,
        user=user_to_response(current_user),
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link via email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Generate a single-use 20-minute reset token and dispatch an email via Resend API."""
    raw_origin = request.headers.get("origin")
    raw_referer = request.headers.get("referer")
    request_base = str(request.base_url) if request.base_url else None
    base_url = resolve_frontend_base_url(
        origin=raw_origin,
        referer=raw_referer,
        request_base_url=request_base,
    )
    return await request_password_reset(session, payload.email, base_url)


@router.get(
    "/verify-reset-token",
    response_model=VerifyResetTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify whether a password reset token is valid",
)
async def verify_token(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    """Check if token exists, has not expired (20 min), and has not been used."""
    await verify_reset_token(session, token)
    return VerifyResetTokenResponse(
        valid=True,
        message="Password reset token is valid.",
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid reset token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Verify single-use token and update user's hashed password in PostgreSQL."""
    return await reset_password_with_token(session, payload)
