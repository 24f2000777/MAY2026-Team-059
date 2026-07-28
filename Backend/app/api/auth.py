"""
Authentication API routes.

Every endpoint here is intentionally thin:

    1. Accept a validated request schema.
    2. Call the matching app.services.auth_service function.
    3. Wrap whatever it returns in the standard success envelope
       (SuccessResponse — see app/schemas/common.py, Appendix B
       of the API design doc) and return that.

No business logic lives in this file — it all lives in
app/services/auth_service.py, which still returns its own plain
domain objects (MessageResponse, TokenResponse, UserResponse)
unchanged; wrapping them for the API contract is a presentation
concern that belongs at the route layer, not the service layer.

If a service function raises a custom exception (see
app/utils/exceptions.py), the global handlers registered in
app/core/exception_handlers.py convert it into the matching
error envelope automatically, so no try/except appears below.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.dependencies.auth import (
    get_current_user,
    get_current_token_payload,
)

from app.model import User

from app.schemas.common import SuccessResponse

from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    LogoutRequest,
    TokenResponse,
    UserResponse,
)

from app.services.auth_service import (
    register_user,
    verify_email,
    resend_verification_otp,
    login_user,
    refresh_access_token,
    forgot_password,
    reset_password,
    update_profile,
    change_password,
    logout_user,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# =====================================================
# Register
# =====================================================

@router.post(
    "/register",
    response_model=SuccessResponse[None],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen account",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    """
    Create a new citizen account and send an email
    verification OTP.

    Raises:
        EmailAlreadyExistsError: 409, if the email is
            already registered and verified.
        PhoneAlreadyExistsError: 409, if the phone number
            is already registered.
    """

    result = await register_user(db, request)
    return SuccessResponse[None](message=result.message)


# =====================================================
# Verify OTP (Email Verification)
# =====================================================

@router.post(
    "/verify-otp",
    response_model=SuccessResponse[TokenResponse],
    summary="Verify a registered email using the OTP sent to it",
)
async def verify_otp_route(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """
    Activate a user's account once the correct OTP is supplied, and
    log them straight in — returns the same access/refresh token pair
    POST /login does, so the client doesn't need a separate login call
    (and doesn't need to hold onto the plaintext password to make one)
    right after verifying.

    Raises:
        UserNotFoundError: 404, if the email is not registered.
        AccountAlreadyVerifiedError: 409, if already verified.
        InvalidOTPError: 400, if the OTP is wrong or expired.
    """

    result = await verify_email(db, request)
    return SuccessResponse[TokenResponse](
        message="Email verified successfully.",
        data=result,
    )


@router.post(
    "/resend-otp",
    response_model=SuccessResponse[None],
    summary="Resend the email verification OTP for a pending account",
)
async def resend_otp_route(
    request: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    """
    Resends the verification OTP without needing to resubmit
    name/phone/password, just the email, for a client that only wants
    a fresh code (e.g. the original one expired or never arrived).

    Raises:
        UserNotFoundError: 404, if the email is not registered.
        AccountAlreadyVerifiedError: 409, if already verified.
        RateLimitExceededError: 429, if requested more than
            OTP_RESEND_RATE_LIMIT_MAX_ATTEMPTS times within
            OTP_RESEND_RATE_LIMIT_WINDOW_SECONDS for this email.
    """

    result = await resend_verification_otp(db, request)
    return SuccessResponse[None](message=result.message)


# =====================================================
# Login
# =====================================================

@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Authenticate and receive access + refresh tokens",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """
    Authenticate a user with email and password.

    Raises:
        InvalidCredentialsError: 401, if email/password is wrong.
        EmailNotVerifiedError: 403, if the account is not yet
            verified.
    """

    result = await login_user(db, request)
    return SuccessResponse[TokenResponse](
        message="Login successful.",
        data=result,
    )


# =====================================================
# Refresh Access Token
# =====================================================

@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Exchange a valid refresh token for a new access token",
)
async def refresh(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """
    Issue a new access token from a valid, unexpired,
    non-revoked refresh token.

    Raises:
        InvalidTokenError: 401 (AUTH_002 if expired, AUTH_003
            otherwise — malformed, wrong type, or revoked
            via logout).
        UserNotFoundError: 404, if the user no longer exists.
        EmailNotVerifiedError: 403, if the account is
            no longer active.
    """

    result = await refresh_access_token(db, request.refresh_token)
    return SuccessResponse[TokenResponse](
        message="Token refreshed successfully.",
        data=result,
    )


# =====================================================
# Forgot Password
# =====================================================

@router.post(
    "/forgot-password",
    response_model=SuccessResponse[None],
    summary="Request a password reset OTP",
)
async def forgot_password_route(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    """
    Send a password reset OTP to a verified user's email.

    Raises:
        RateLimitExceededError: 429, if requested more than
            3 times in the last hour for this email.
        UserNotFoundError: 404, if the email is not registered.
        EmailNotVerifiedError: 403, if the account has not
            been verified yet.
    """

    result = await forgot_password(db, request)
    return SuccessResponse[None](message=result.message)


# =====================================================
# Reset Password
# =====================================================

@router.post(
    "/reset-password",
    response_model=SuccessResponse[None],
    summary="Reset password using the OTP sent via forgot-password",
)
async def reset_password_route(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    """
    Set a new password after verifying the reset OTP.

    Raises:
        UserNotFoundError: 404, if the email is not registered.
        EmailNotVerifiedError: 403, if the account is not verified.
        InvalidOTPError: 400, if the OTP is wrong or expired.
        InvalidCredentialsError: 400, if the new password is
            the same as the current one.
    """

    result = await reset_password(db, request)
    return SuccessResponse[None](message=result.message)


# =====================================================
# Get Own Profile
# =====================================================

@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get the current authenticated user's profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    """
    Return the profile of whoever the bearer access token
    belongs to. Pure passthrough — no service call needed
    since get_current_user has already loaded the user.
    """

    return SuccessResponse[UserResponse](
        message="Profile retrieved successfully.",
        data=UserResponse.model_validate(current_user),
    )


# =====================================================
# Update Own Profile
# =====================================================

@router.put(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Update the current user's name and/or phone number",
)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[UserResponse]:
    """
    Update the current user's own name and/or phone number.
    Email and address are not editable through this endpoint.

    Raises:
        PhoneAlreadyExistsError: 409, if the new phone number
            is already registered to a different account.
    """

    result = await update_profile(db, current_user, request)
    return SuccessResponse[UserResponse](
        message="Profile updated successfully.",
        data=result,
    )


# =====================================================
# Change Password
# =====================================================

@router.post(
    "/change-password",
    response_model=SuccessResponse[None],
    summary="Change the current user's password",
)
async def change_my_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[None]:
    """
    Change the current (already logged-in) user's password.

    Raises:
        InvalidCredentialsError: 401, if the current
            password is wrong, or the new password is the
            same as the current one.
    """

    result = await change_password(db, current_user, request)
    return SuccessResponse[None](message=result.message)


# =====================================================
# Logout
# =====================================================

@router.post(
    "/logout",
    response_model=SuccessResponse[None],
    summary="Log out — revoke the current access token (and refresh token, if provided)",
)
async def logout(
    request: LogoutRequest,
    token_payload: dict = Depends(get_current_token_payload),
) -> SuccessResponse[None]:
    """
    Revoke the current session's tokens via the Redis
    blacklist. The access token is always revoked (it's the
    one used to authenticate this request). The refresh token
    is also revoked if supplied in the request body.
    """

    result = await logout_user(
        token_payload,
        request.refresh_token,
    )
    return SuccessResponse[None](message=result.message)