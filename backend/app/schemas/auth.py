from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=160, description="User's full name")
    email: str = Field(..., min_length=3, max_length=320, description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="Account password (min 6 chars)")
    confirm_password: Optional[str] = Field(None, description="Password confirmation")


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320, description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    full_name: Optional[str] = None
    education: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    success: bool = True
    message: str = "Authentication successful"
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthMeResponse(BaseModel):
    success: bool = True
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320, description="User email address")


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Password reset link has been sent to your registered email address."


class VerifyResetTokenResponse(BaseModel):
    valid: bool = True
    message: str = "Password reset token is valid."


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Password reset token from email link")
    password: str = Field(..., min_length=6, max_length=128, description="New password (min 6 chars)")
    confirm_password: Optional[str] = Field(None, description="Confirm new password")


class ResetPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Your password has been successfully reset. You can now sign in with your new password."
