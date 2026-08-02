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

import re

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

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
    InsufficientPermissionsError,
    ChatSessionAccessDeniedError,
    ComplaintError,
    ComplaintNotFoundError,
    InvalidStaffAssignmentError,
    ComplaintNotAssignableError,
    InvalidStatusTransitionError,
    ComplaintNotAssignedToUserError,
    ComplaintNotOwnerError,
    AttachmentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    TooManyAttachmentsError,
    AttachmentNotFoundError,
    NotificationError,
    NotificationNotFoundError,
)


def _error_response(
    status_code: int,
    exc: AuthenticationError | ComplaintError | AttachmentError,
    details: dict | None = None,
) -> JSONResponse:
    """
    Build the standard error envelope (Appendix B).

    error_code is read straight off the exception instance —
    every AuthenticationError/ComplaintError subclass carries a
    default error_code, and specific raise sites can override it
    per instance (e.g. InvalidTokenError distinguishing AUTH_002
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


async def handle_insufficient_permissions(
    request: Request,
    exc: InsufficientPermissionsError,
) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc)


async def handle_chat_session_access_denied(
    request: Request,
    exc: ChatSessionAccessDeniedError,
) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc)


async def handle_complaint_not_found(
    request: Request,
    exc: ComplaintNotFoundError,
) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc)


async def handle_invalid_staff_assignment(
    request: Request,
    exc: InvalidStaffAssignmentError,
) -> JSONResponse:
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, exc)


async def handle_complaint_not_assignable(
    request: Request,
    exc: ComplaintNotAssignableError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_invalid_status_transition(
    request: Request,
    exc: InvalidStatusTransitionError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_complaint_not_assigned_to_user(
    request: Request,
    exc: ComplaintNotAssignedToUserError,
) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc)


async def handle_complaint_not_owner(
    request: Request,
    exc: ComplaintNotOwnerError,
) -> JSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc)


async def handle_complaint_error(
    request: Request,
    exc: ComplaintError,
) -> JSONResponse:
    """
    Fallback for any ComplaintError subclass that does not have a
    more specific handler registered above, same reasoning as
    handle_authentication_error below.
    """
    return _error_response(status.HTTP_400_BAD_REQUEST, exc)


async def handle_file_too_large(
    request: Request,
    exc: FileTooLargeError,
) -> JSONResponse:
    return _error_response(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, exc)


async def handle_unsupported_file_type(
    request: Request,
    exc: UnsupportedFileTypeError,
) -> JSONResponse:
    return _error_response(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, exc)


async def handle_too_many_attachments(
    request: Request,
    exc: TooManyAttachmentsError,
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


async def handle_attachment_not_found(
    request: Request,
    exc: AttachmentNotFoundError,
) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc)


async def handle_attachment_error(
    request: Request,
    exc: AttachmentError,
) -> JSONResponse:
    """
    Fallback for any AttachmentError subclass that does not have a
    more specific handler registered above, same reasoning as
    handle_complaint_error above.
    """
    return _error_response(status.HTTP_400_BAD_REQUEST, exc)


async def handle_notification_not_found(
    request: Request,
    exc: NotificationNotFoundError,
) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc)


async def handle_notification_error(
    request: Request,
    exc: NotificationError,
) -> JSONResponse:
    """
    Fallback for any NotificationError subclass that does not have a
    more specific handler registered above, same reasoning as
    handle_complaint_error above.
    """
    return _error_response(status.HTTP_400_BAD_REQUEST, exc)


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


# Matches the "CODE: message" shape a custom validator's ValueError
# subclass raises (see app/schemas/complaint.py's LocationValidationError),
# preserved by pydantic in each error's ctx.error as the exception's own
# str(), unprefixed by pydantic's own "Value error, " wrapping of msg.
_STRUCTURED_ERROR_CODE = re.compile(r"^(VAL_\d{3}): ")


def _validation_error_code(exc: RequestValidationError) -> str:
    """
    Most request validation failures (missing field, wrong type, an
    out-of-range Field constraint) have no more specific code than the
    generic VAL_001. But a validator that raises its own CODE-prefixed
    ValueError subclass (e.g. ComplaintLocation's VAL_001/VAL_002 split)
    wants that specific code surfaced instead of being collapsed into
    VAL_001 for every kind of location error alike.
    """
    for error in exc.errors():
        message = error.get("ctx", {}).get("error")
        if message:
            match = _STRUCTURED_ERROR_CODE.match(str(message))
            if match:
                return match.group(1)
    return "VAL_001"


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
            "error_code": _validation_error_code(exc),
            "details": {"errors": jsonable_encoder(exc.errors())},
        },
    )


async def handle_integrity_error(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """
    Catches raw database unique constraint violations (e.g. from race conditions
    during registration). Looks at the raw error string to determine whether
    the conflict was email or phone, and returns the standard envelope.
    """
    
    error_str = str(exc.orig).lower() if exc.orig else str(exc).lower()
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
    
    if "users_phone_key" in error_str or "phone" in constraint:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "message": "Phone number is already registered.",
                "error_code": "AUTH_008",
                "details": None,
            },
        )
    
    # Default to email
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "message": "Email is already registered.",
            "error_code": "AUTH_007",
            "details": None,
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

    app.add_exception_handler(
        InsufficientPermissionsError,
        handle_insufficient_permissions,
    )

    app.add_exception_handler(
        ChatSessionAccessDeniedError,
        handle_chat_session_access_denied,
    )

    # Catch-all fallback for any other AuthenticationError subclass.
    app.add_exception_handler(
        AuthenticationError,
        handle_authentication_error,
    )

    app.add_exception_handler(
        ComplaintNotFoundError,
        handle_complaint_not_found,
    )

    app.add_exception_handler(
        InvalidStaffAssignmentError,
        handle_invalid_staff_assignment,
    )

    app.add_exception_handler(
        ComplaintNotAssignableError,
        handle_complaint_not_assignable,
    )

    app.add_exception_handler(
        InvalidStatusTransitionError,
        handle_invalid_status_transition,
    )

    app.add_exception_handler(
        ComplaintNotAssignedToUserError,
        handle_complaint_not_assigned_to_user,
    )

    app.add_exception_handler(
        ComplaintNotOwnerError,
        handle_complaint_not_owner,
    )

    # Catch-all fallback for any other ComplaintError subclass.
    app.add_exception_handler(
        ComplaintError,
        handle_complaint_error,
    )

    app.add_exception_handler(
        FileTooLargeError,
        handle_file_too_large,
    )

    app.add_exception_handler(
        UnsupportedFileTypeError,
        handle_unsupported_file_type,
    )

    app.add_exception_handler(
        TooManyAttachmentsError,
        handle_too_many_attachments,
    )

    app.add_exception_handler(
        AttachmentNotFoundError,
        handle_attachment_not_found,
    )

    # Catch-all fallback for any other AttachmentError subclass.
    app.add_exception_handler(
        AttachmentError,
        handle_attachment_error,
    )

    app.add_exception_handler(
        NotificationNotFoundError,
        handle_notification_not_found,
    )

    # Catch-all fallback for any other NotificationError subclass.
    app.add_exception_handler(
        NotificationError,
        handle_notification_error,
    )

    # FastAPI/Pydantic's own request validation errors (422),
    # wrapped in the same envelope as everything else.
    app.add_exception_handler(
        RequestValidationError,
        handle_validation_error,
    )
    
    # Handle database integrity errors (e.g. race conditions)
    app.add_exception_handler(
        IntegrityError,
        handle_integrity_error,
    )