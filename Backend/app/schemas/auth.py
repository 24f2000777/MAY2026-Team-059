"""
Authentication request and response schemas.

These schemas define the contract between the frontend
and the backend.

They are NOT database models.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from uuid import UUID


# =====================================================
# Register
# =====================================================

class RegisterRequest(BaseModel):
    """
    Request body for user registration.
    """

    name: str = Field(..., min_length=2, max_length=100)

    phone: str = Field(..., min_length=10, max_length=15)

    email: EmailStr

    password: str = Field(..., min_length=8, max_length=128)


# =====================================================
# Verify OTP
# =====================================================

class VerifyOTPRequest(BaseModel):
    """
    Request body for email OTP verification.
    """

    email: EmailStr

    otp: str = Field(..., min_length=6, max_length=6)


# =====================================================
# Login
# =====================================================

class LoginRequest(BaseModel):
    """
    Login using email and password.
    """

    email: EmailStr

    password: str


# =====================================================
# Refresh Token
# =====================================================

class RefreshTokenRequest(BaseModel):
    """
    Request body for refreshing an access token.
    """

    refresh_token: str


# =====================================================
# Forgot Password
# =====================================================

class ForgotPasswordRequest(BaseModel):
    """
    Request body for requesting a password reset.
    """

    email: EmailStr


# =====================================================
# Reset Password
# =====================================================

class ResetPasswordRequest(BaseModel):
    """
    Reset password using email + OTP.
    """

    email: EmailStr

    otp: str = Field(..., min_length=6, max_length=6)

    new_password: str = Field(..., min_length=8, max_length=128)




# =====================================================
# User Response
# =====================================================

class UserResponse(BaseModel):
    """
    Public user information.
    """

    id: UUID

    name: str

    phone: str

    email: EmailStr

    role: str

    is_active: bool
    
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================
# Authentication Response
# =====================================================

class TokenResponse(BaseModel):
    """
    Response returned after successful login.
    """

    access_token: str

    refresh_token: str

    token_type: str = "bearer"
    
    user: UserResponse
    
# =====================================================
# Generic Message Response
# =====================================================

class MessageResponse(BaseModel):
    """
    Generic success response.
    """

    message: str
    
# =====================================================
# Resend OTP
# =====================================================

class ResendOTPRequest(BaseModel):
    """
    Request body for resending email verification OTP.
    """

    email: EmailStr