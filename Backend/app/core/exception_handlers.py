"""
Global exception handlers.

Converts custom domain exceptions (raised by the service layer)
into consistent JSON HTTP responses, using the standard error
envelope from Appendix B of the API design doc:

    {
        "success": false,
        "message": "<human readable message>",
        "error_code": "AUTH_001",
        "details": null
    }

This keeps API routes thin — routes never need try/except blocks
for known business errors. A route simply calls a service function;
if that function raises, FastAPI intercepts it here before it ever
reaches the client.

Registered once in app/main.py via app.add_exception_handler(),
so every router (auth, complaints, officer, admin, ...) benefits
automatically without duplicating error-handling logic anywhere.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    PhoneAlreadyExistsError,
    AccountAlreadyVerifiedError,
    UserNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    EmailNotVerifiedError,
    InvalidOTPError,
    RateLimitExceededError,
)


def _error_response(
    status_code: int,
    exc: AuthenticationError,
    details: dict | None = None,
) -> JSONResponse:
    """
    Build the standard error envelope (Appendix B).

    error_code is read straight off the exception instance —
    every AuthenticationError subclass carries a default
    error_code, and specific raise sites can override it per
    instance (e.g. InvalidTokenError distinguishing AUTH_002
    "expired" from AUTH_003 "invalid") — so this function never
    needs to know about individual exception types itself.
    """

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": str(exc),
            "error_code": exc.error_code,
            "details": details,
        },
    )


# =====================================================
# Individual Handlers
# =====================================================
#
# Each handler is intentionally a separate small function
# (rather than one giant if/elif chain) so that new exception
# types can be added independently as new modules are built,
# without touching existing mappings.


async def handle_email_already_exists(
    request: Request,
    exc: EmailAlreadyExistsError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_phone_already_exists(
    request: Request,
    exc: PhoneAlreadyExistsError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_account_already_verified(
    request: Request,
    exc: AccountAlreadyVerifiedError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_user_not_found(
    request: Request,
    exc: UserNotFoundError,
) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc)


async def handle_invalid_credentials(
    request: Request,
    exc: InvalidCredentialsError,
) -> JSONResponse:
    return _error_response(status.HTTP_401_UNAUTHORIZED, exc)


async def handle_invalid_token(
    request: Request,
    exc: InvalidTokenError,
) -> JSONResponse:
    return _error_response(status.HTTP_401_UNAUTHORIZED, exc)


async def handle_email_not_verified(
    request: Request,
    exc: EmailNotVerifiedError,
) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc)


async def handle_invalid_otp(
    request: Request,
    exc: InvalidOTPError,
) -> JSONResponse:
    return _error_response(status.HTTP_400_BAD_REQUEST, exc)


async def handle_rate_limit_exceeded(
    request: Request,
    exc: RateLimitExceededError,
) -> JSONResponse:
    return _error_response(status.HTTP_429_TOO_MANY_REQUESTS, exc)


async def handle_authentication_error(
    request: Request,
    exc: AuthenticationError,
) -> JSONResponse:
    """
    Fallback for any AuthenticationError subclass that does not
    have a more specific handler registered above.

    Acts as a safety net so a newly added exception type never
    leaks as an unhandled 500 error just because its handler
    was forgotten.
    """

    return _error_response(status.HTTP_400_BAD_REQUEST, exc)


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Wraps FastAPI/Pydantic's own request validation failures
    (bad request bodies, wrong types, missing required fields)
    in the same envelope as every other error — Appendix C's
    VAL_001, which otherwise would bypass this envelope
    entirely since it's raised by FastAPI itself, not by our
    service layer.
    """

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Request validation failed.",
            "error_code": "VAL_001",
            "details": {"errors": jsonable_encoder(exc.errors())},
        },
    )


# =====================================================
# Registration
# =====================================================


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all custom exception handlers to the FastAPI app.

    Order matters for FastAPI's lookup in one respect only:
    more specific exception types should be registered alongside
    (not necessarily before) their base class — FastAPI always
    matches the most specific registered type first, so the
    AuthenticationError fallback is safe to register last.

    Call this once, from app/main.py, right after creating `app`.
    """

    app.add_exception_handler(
        EmailAlreadyExistsError,
        handle_email_already_exists,
    )

    app.add_exception_handler(
        PhoneAlreadyExistsError,
        handle_phone_already_exists,
    )

    app.add_exception_handler(
        AccountAlreadyVerifiedError,
        handle_account_already_verified,
    )

    app.add_exception_handler(
        UserNotFoundError,
        handle_user_not_found,
    )

    app.add_exception_handler(
        InvalidCredentialsError,
        handle_invalid_credentials,
    )

    app.add_exception_handler(
        InvalidTokenError,
        handle_invalid_token,
    )

    app.add_exception_handler(
        EmailNotVerifiedError,
        handle_email_not_verified,
    )

    app.add_exception_handler(
        InvalidOTPError,
        handle_invalid_otp,
    )

    app.add_exception_handler(
        RateLimitExceededError,
        handle_rate_limit_exceeded,
    )

    # Catch-all fallback for any other AuthenticationError subclass.
    app.add_exception_handler(
        AuthenticationError,
        handle_authentication_error,
    )

    # FastAPI/Pydantic's own request validation errors (422),
    # wrapped in the same envelope as everything else.
    app.add_exception_handler(
        RequestValidationError,
        handle_validation_error,
    )