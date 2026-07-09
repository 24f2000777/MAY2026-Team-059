"""
Authentication Service

Business logic for:

- Register
- Verify Email
- Login
- Refresh Token
- Forgot Password
- Reset Password
- Update Profile
- Change Password
- Logout

This module contains NO FastAPI routes.

Routes should call these service functions.
"""

from __future__ import annotations

from uuid import UUID
import asyncio

from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model import User

from app.core.config import settings

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    DUMMY_PASSWORD_HASH,
    JWT_SUB,
    JWT_TYPE,
    JWT_JTI,
    JWT_EXP,
)

from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    TokenResponse,
    MessageResponse,
    UserResponse,
)

from app.services.email_service import (
    send_verification_email,
    send_password_reset_email,
)

from app.services.otp_service import (
    create_otp,
    verify_otp,
    delete_otp,
)

from app.services.token_blacklist_service import (
    blacklist_token,
    is_token_blacklisted,
)

from app.services.rate_limit_service import enforce_rate_limit


from app.utils.constants import (
    ROLE_CITIZEN,
    OTP_VERIFY_EMAIL,
    OTP_RESET_PASSWORD,
    ACCESS_TOKEN,
    REFRESH_TOKEN,
)


from app.utils.exceptions import (
    AccountAlreadyVerifiedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidOTPError,
    InvalidTokenError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
    UserNotFoundError,
)



# =====================================================
# Private Helper Functions
# =====================================================

async def _get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    """
    Fetch a user by email.

    Returns:
        User object if found, otherwise None.
    """

    result = await db.execute(
        select(User).where(User.email == email)
    )

    return result.scalar_one_or_none()


async def _get_user_by_phone(
    db: AsyncSession,
    phone: str,
) -> User | None:
    """
    Fetch a user by phone number.

    Returns:
        User object if found, otherwise None.
    """

    result = await db.execute(
        select(User).where(User.phone == phone)
    )

    return result.scalar_one_or_none()


async def _get_user_by_id(
    db: AsyncSession,
    user_id: UUID,
) -> User | None:
    """
    Fetch a user by UUID.

    Returns:
        User object if found, otherwise None.
    """

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    return result.scalar_one_or_none()


async def _send_verification_otp(
    email: str,
) -> None:
    """
    Generate and send an email verification OTP.

    The actual SMTP call (smtplib.SMTP, inside
    send_verification_email) is a blocking network call.
    Running it directly inside this async function would
    block the whole event loop — every other concurrent
    request on this worker would stall for however long SMTP
    takes to respond. asyncio.to_thread offloads it to a
    separate thread, so this coroutine still waits for the
    result (the caller gets the same success/failure
    guarantee as before) without blocking anyone else's
    requests while it waits.

    Deletes the OTP from Redis if email delivery fails.
    """

    otp = await create_otp(
        email=email,
        purpose=OTP_VERIFY_EMAIL,
    )

    try:
        await asyncio.to_thread(
            send_verification_email,
            recipient=email,
            otp=otp,
        )

    except Exception:
        await delete_otp(
            email=email,
            purpose=OTP_VERIFY_EMAIL,
        )
        raise


async def _send_reset_password_otp(
    email: str,
) -> None:
    """
    Generate and send a password reset OTP.

    See _send_verification_otp's docstring — same
    asyncio.to_thread reasoning applies here.
    """

    otp = await create_otp(
        email=email,
        purpose=OTP_RESET_PASSWORD,
    )

    try:
        await asyncio.to_thread(
            send_password_reset_email,
            recipient=email,
            otp=otp,
        )

    except Exception:
        await delete_otp(
            email=email,
            purpose=OTP_RESET_PASSWORD,
        )
        raise

# =====================================================
# Register User
# =====================================================

async def register_user(
    db: AsyncSession,
    request: RegisterRequest,
) -> MessageResponse:
    """
    Register a new citizen account and send
    an email verification OTP.

    Flow
    ----
    1. Check email uniqueness.
    2. Check phone uniqueness.
    3. Create inactive account.
    4. Flush to database.
    5. Send verification OTP.
    6. Return success message.

    Note:
        The database transaction is committed by the
        get_db() dependency after the request completes.

    Note on user enumeration:
        This intentionally tells the caller when an email is
        already registered (both here and via the "pending
        verification" branch below) — this matches near-
        universal industry practice for registration flows
        (almost every consumer product does this, since a
        silent/generic response would make "did my signup
        work?" impossible to answer). This is a deliberate,
        accepted tradeoff, not an oversight. Contrast with
        login_user, where the equivalent timing side-channel
        IS closed, because there the leak is more severe (it
        would help credential-stuffing against accounts the
        attacker already suspects exist) and closing it costs
        nothing user-facing.
    """

    # -------------------------------------------------
    # Email already registered?
    # -------------------------------------------------

    existing_user = await _get_user_by_email(
        db,
        request.email,
    )

    if existing_user is not None:

        # Account already verified
        if existing_user.is_active:
            raise EmailAlreadyExistsError(
                "Email is already registered."
            )

        # Account exists but email not verified
        await _send_verification_otp(
            existing_user.email,
        )

        return MessageResponse(
            message=(
                "Your account is pending verification. "
                "A new verification OTP has been sent."
            )
        )

    # -------------------------------------------------
    # Phone already registered?
    # -------------------------------------------------

    existing_phone = await _get_user_by_phone(
        db,
        request.phone,
    )

    if existing_phone is not None:
        raise PhoneAlreadyExistsError(
            "Phone number is already registered."
        )

    # -------------------------------------------------
    # Create new user
    # -------------------------------------------------

    user = User(
        name=request.name,
        phone=request.phone,
        email=request.email,
        role=ROLE_CITIZEN,
        hashed_password=hash_password(
            request.password,
        ),
        is_active=False,
    )

    db.add(user)

    # Flush pending INSERT so the generated UUID
    # is available before sending the verification email.
    await db.flush()

    # -------------------------------------------------
    # Send verification email
    # -------------------------------------------------

    await _send_verification_otp(
        user.email,
    )


    return MessageResponse(
        message=(
            "Registration successful. "
            "A verification OTP has been sent to your email."
        )
    )



# =====================================================
# Verify Email
# =====================================================

async def verify_email(
    db: AsyncSession,
    request: VerifyOTPRequest,
) -> MessageResponse:
    """
    Verify a user's email using the OTP sent to
    their registered email address.

    Flow
    ----
    1. Find user.
    2. Ensure account is not already active.
    3. Enforce rate limit on verification attempts (a 6-digit
       OTP is guessable if attempts are unlimited within its
       5-minute lifetime).
    4. Verify OTP from Redis.
    5. Activate account.
    6. Return success message.
    """

    user = await _get_user_by_email(
        db,
        request.email,
    )

    if user is None:
        raise UserNotFoundError(
            "User does not exist."
        )

    # -------------------------------------------------
    # Already verified?
    # -------------------------------------------------

    if user.is_active:
        raise AccountAlreadyVerifiedError(
            "Account is already verified."
        )

    # -------------------------------------------------
    # Rate limit verification attempts against this OTP
    # -------------------------------------------------

    await enforce_rate_limit(
        scope="verify_otp_attempt",
        identifier=request.email,
        max_attempts=settings.OTP_VERIFY_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.OTP_VERIFY_RATE_LIMIT_WINDOW_SECONDS,
    )

    # -------------------------------------------------
    # Verify OTP
    # -------------------------------------------------

    is_valid = await verify_otp(
        email=request.email,
        otp=request.otp,
        purpose=OTP_VERIFY_EMAIL,
    )

    if not is_valid:
        raise InvalidOTPError(
            "Invalid or expired OTP."
        )

    # -------------------------------------------------
    # Activate account
    # -------------------------------------------------

    user.is_active = True

    await db.flush()

    return MessageResponse(
        message=(
            "Email verified successfully."
        )
    )


# =====================================================
# Login User
# =====================================================

async def login_user(
    db: AsyncSession,
    request: LoginRequest,
) -> TokenResponse:
    """
    Authenticate a user.

    Flow
    ----
    1. Find user by email.
    2. Verify password.
    3. Ensure account is verified.
    4. Generate access token.
    5. Generate refresh token.
    6. Return authentication response.

    Note on timing safety:
        If no user is found, a real bcrypt verification is
        still performed (against DUMMY_PASSWORD_HASH) before
        raising. bcrypt is deliberately slow (~100-300ms) —
        skipping it entirely for unknown emails while
        performing it for known ones would create a
        measurable timing difference, letting a caller
        distinguish "no such account" from "wrong password"
        purely by how long the response took, even though
        both return the identical 401 body. Always doing the
        same bcrypt work regardless of whether the user
        exists closes that side channel.
    """

    # -------------------------------------------------
    # Find user
    # -------------------------------------------------

    user = await _get_user_by_email(
        db,
        request.email,
    )

    if user is None:
        # Burn the same bcrypt time a real verification would
        # take, so this branch and the "wrong password" branch
        # below are indistinguishable by response time.
        verify_password(
            request.password,
            DUMMY_PASSWORD_HASH,
        )

        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    # -------------------------------------------------
    # Verify password
    # -------------------------------------------------

    if not verify_password(
        request.password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError(
            "Invalid email or password."
        )

    # -------------------------------------------------
    # Email verified?
    # -------------------------------------------------

    if not user.is_active:
        raise EmailNotVerifiedError(
            "Please verify your email before logging in."
        )

    # -------------------------------------------------
    # Generate JWT Tokens
    # -------------------------------------------------

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    refresh_token = create_refresh_token(
        user_id=str(user.id),
        role=user.role,
    )

    # -------------------------------------------------
    # Return Response
    # -------------------------------------------------

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )



# =====================================================
# Refresh Access Token
# =====================================================

async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """
    Generate a new access token AND a new refresh token from a
    valid, unexpired, non-revoked refresh token — rotating the
    refresh token on every use.

    Rotation means each refresh token is single-use: the one
    presented here is immediately blacklisted (the blacklist
    infrastructure already exists for logout, so this reuses
    it rather than adding a new mechanism), and a brand new
    refresh token is issued alongside the new access token. If
    a refresh token is ever stolen, it's only useful until the
    legitimate client's next refresh — after that, both the
    thief's copy and the legitimate client's copy of the OLD
    token are dead, which surfaces the theft immediately
    instead of leaving a long-lived, silently-reusable token
    valid for its full 7-day lifetime.
    """

    # -------------------------------------------------
    # Decode JWT
    # -------------------------------------------------

    try:
        payload = decode_token(
            refresh_token,
        )

    except ExpiredSignatureError as exc:
        raise InvalidTokenError(
            "Refresh token has expired.",
            error_code="AUTH_002",
        ) from exc

    except JWTError as exc:
        raise InvalidTokenError(
            "Invalid refresh token.",
            error_code="AUTH_003",
        ) from exc

    # -------------------------------------------------
    # Verify token type
    # -------------------------------------------------

    if payload.get(JWT_TYPE) != REFRESH_TOKEN:
        raise InvalidTokenError(
            "Invalid refresh token."
        )

    # -------------------------------------------------
    # Revoked via logout or a previous refresh?
    # -------------------------------------------------

    if await is_token_blacklisted(payload.get(JWT_JTI)):
        raise InvalidTokenError(
            "Refresh token has been revoked."
        )

    # -------------------------------------------------
    # Extract user id
    # -------------------------------------------------

    user_id = payload.get(JWT_SUB)

    if user_id is None:
        raise InvalidTokenError(
            "Invalid refresh token."
        )

    # -------------------------------------------------
    # Validate UUID
    # -------------------------------------------------

    try:
        user_uuid = UUID(user_id)

    except (TypeError, ValueError) as exc:
        raise InvalidTokenError(
            "Invalid refresh token."
        ) from exc

    # -------------------------------------------------
    # Find user
    # -------------------------------------------------
    user = await _get_user_by_id(
        db,
        user_uuid,
    )

    if user is None:
        raise UserNotFoundError(
            "User not found."
        )

    # -------------------------------------------------
    # User still active?
    # -------------------------------------------------

    if not user.is_active:
        raise EmailNotVerifiedError(
            "Account is not active."
        )

    # -------------------------------------------------
    # Rotate: retire the presented refresh token...
    # -------------------------------------------------

    await blacklist_token(
        jti=payload.get(JWT_JTI),
        expires_at=payload.get(JWT_EXP),
    )

    # -------------------------------------------------
    # ...and issue a brand new access + refresh pair
    # -------------------------------------------------

    new_access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    new_refresh_token = create_refresh_token(
        user_id=str(user.id),
        role=user.role,
    )

    # -------------------------------------------------
    # Return response
    # -------------------------------------------------

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )




# =====================================================
# Forgot Password
# =====================================================

async def forgot_password(
    db: AsyncSession,
    request: ForgotPasswordRequest,
) -> MessageResponse:
    """
    Generate and send a password reset OTP.

    Flow
    ----
    1. Enforce rate limit (max attempts per hour per email).
    2. Find user.
    3. Ensure account is verified.
    4. Send password reset OTP.
    5. Return success message.
    """

    # -------------------------------------------------
    # Rate limit — checked first, before revealing
    # anything about whether the email is registered,
    # so this can't be used as an unlimited-attempt
    # enumeration oracle either.
    # -------------------------------------------------

    await enforce_rate_limit(
        scope="forgot_password",
        identifier=request.email,
        max_attempts=settings.PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
    )

    # -------------------------------------------------
    # Find user
    # -------------------------------------------------

    user = await _get_user_by_email(
        db,
        request.email,
    )

    if user is None:
        raise UserNotFoundError(
            "User not found."
        )

    # -------------------------------------------------
    # Account verified?
    # -------------------------------------------------

    if not user.is_active:
        raise EmailNotVerifiedError(
            "Account has not been verified."
        )

    # -------------------------------------------------
    # Send password reset OTP
    # -------------------------------------------------

    await _send_reset_password_otp(
        user.email,
    )

    return MessageResponse(
        message=(
            "Password reset OTP has been sent "
            "to your email."
        )
    )



# =====================================================
# Reset Password
# =====================================================

async def reset_password(
    db: AsyncSession,
    request: ResetPasswordRequest,
) -> MessageResponse:
    """
    Reset a user's password after
    successful OTP verification.

    Flow
    ----
    1. Find user.
    2. Ensure account is verified.
    3. Enforce rate limit on verification attempts against
       this OTP (same brute-force concern as verify_email).
    4. Verify OTP.
    5. Update password.
    """

    # -------------------------------------------------
    # Find user
    # -------------------------------------------------

    user = await _get_user_by_email(
        db,
        request.email,
    )

    if user is None:
        raise UserNotFoundError(
            "User not found."
        )

    # -------------------------------------------------
    # Account verified?
    # -------------------------------------------------

    if not user.is_active:
        raise EmailNotVerifiedError(
            "Account has not been verified."
        )

    # -------------------------------------------------
    # Rate limit verification attempts against this OTP
    # -------------------------------------------------

    await enforce_rate_limit(
        scope="reset_otp_attempt",
        identifier=request.email,
        max_attempts=settings.OTP_VERIFY_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds=settings.OTP_VERIFY_RATE_LIMIT_WINDOW_SECONDS,
    )

    # -------------------------------------------------
    # Verify OTP
    # -------------------------------------------------

    is_valid = await verify_otp(
        email=request.email,
        otp=request.otp,
        purpose=OTP_RESET_PASSWORD,
    )

    if not is_valid:
        raise InvalidOTPError(
            "Invalid or expired OTP."
        )

    # -------------------------------------------------
    # Update password
    # -------------------------------------------------

    if verify_password(
        request.new_password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError(
            "New password must be different from the current password."
        )

    user.hashed_password = hash_password(
        request.new_password
    )

    await db.flush()

    return MessageResponse(
        message="Password reset successfully."
    )



# =====================================================
# Update Profile
# =====================================================

async def update_profile(
    db: AsyncSession,
    user: User,
    request: UpdateProfileRequest,
) -> UserResponse:
    """
    Update the current user's own name and/or phone number.

    Email and address are intentionally not editable through
    this endpoint — see UpdateProfileRequest's docstring for
    why. Fields left as None in the request are left
    unchanged.

    Flow
    ----
    1. If phone is being changed, check it isn't already
       registered to a different account.
    2. Apply any provided field changes.
    3. Return the updated profile.
    """

    # -------------------------------------------------
    # Phone uniqueness (only if actually changing it)
    # -------------------------------------------------

    if request.phone is not None and request.phone != user.phone:

        existing_phone = await _get_user_by_phone(
            db,
            request.phone,
        )

        if existing_phone is not None:
            raise PhoneAlreadyExistsError(
                "Phone number is already registered."
            )

        user.phone = request.phone

    # -------------------------------------------------
    # Name
    # -------------------------------------------------

    if request.name is not None:
        user.name = request.name

    await db.flush()

    return UserResponse.model_validate(user)



# =====================================================
# Change Password
# =====================================================

async def change_password(
    db: AsyncSession,
    user: User,
    request: ChangePasswordRequest,
) -> MessageResponse:
    """
    Change the current (already logged-in) user's password.

    Distinct from forgot_password/reset_password, which are
    OTP-based for users who cannot log in. This flow instead
    requires the user's current password as proof of identity.

    Flow
    ----
    1. Verify the supplied current password matches.
    2. Reject if the new password is identical to the old one.
    3. Hash and store the new password.
    """

    if not verify_password(
        request.current_password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError(
            "Current password is incorrect."
        )

    if verify_password(
        request.new_password,
        user.hashed_password,
    ):
        raise InvalidCredentialsError(
            "New password must be different from the current password."
        )

    user.hashed_password = hash_password(
        request.new_password
    )

    await db.flush()

    return MessageResponse(
        message="Password changed successfully."
    )



# =====================================================
# Logout
# =====================================================

async def logout_user(
    access_token_payload: dict,
    refresh_token: str | None = None,
) -> MessageResponse:
    """
    Revoke the current session's tokens.

    Always revokes the access token whose decoded payload is
    passed in (the one used to authenticate this very request).
    Optionally also revokes a refresh token, if the client
    supplies one in the request body — without it, the refresh
    token remains valid until it naturally expires (or until
    it's next used, since refresh_access_token now rotates it).

    A refresh token that is already malformed or expired is
    treated as "nothing to revoke" rather than an error, since
    the end result the caller wants — that token not working
    anymore — is already true.

    Flow
    ----
    1. Blacklist the access token's jti.
    2. If a refresh token was supplied and is a valid,
       well-formed refresh token, blacklist its jti too.
    """

    await blacklist_token(
        jti=access_token_payload.get(JWT_JTI),
        expires_at=access_token_payload.get(JWT_EXP),
    )

    if refresh_token:

        try:
            refresh_payload = decode_token(refresh_token)

        except JWTError:
            refresh_payload = None

        if (
            refresh_payload is not None
            and refresh_payload.get(JWT_TYPE) == REFRESH_TOKEN
        ):
            await blacklist_token(
                jti=refresh_payload.get(JWT_JTI),
                expires_at=refresh_payload.get(JWT_EXP),
            )

    return MessageResponse(
        message="Logged out successfully."
    )