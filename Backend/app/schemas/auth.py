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


# =====================================================
# Update Profile
# =====================================================

class UpdateProfileRequest(BaseModel):
    """
    Request body for updating the current user's own profile.

    Only name and phone are editable here. Email is
    intentionally excluded — changing it would invalidate
    the account's verification status and needs its own
    re-verification flow, not a plain field update. Address
    is not part of the current User model.

    Both fields are optional so a caller can update just one
    of them; at least one should be provided by the client,
    though the service layer treats "nothing changed" as a
    harmless no-op rather than an error.
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=15,
    )


# =====================================================
# Change Password
# =====================================================

class ChangePasswordRequest(BaseModel):
    """
    Request body for changing the current user's password
    while already logged in (distinct from the OTP-based
    forgot/reset-password flow).
    """

    current_password: str

    new_password: str = Field(..., min_length=8, max_length=128)


# =====================================================
# Logout
# =====================================================

class LogoutRequest(BaseModel):
    """
    Request body for logout.

    The access token being logged out is taken from the
    Authorization header, not this body. refresh_token is
    optional here so a client can also invalidate its refresh
    token in the same call — without it, only the access
    token is blacklisted and the refresh token remains valid
    until it naturally expires.
    """

    refresh_token: str | None = None