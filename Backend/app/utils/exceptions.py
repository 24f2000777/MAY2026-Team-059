"""
Custom exceptions for the application.

The service layer raises these exceptions.

The API layer converts them into HTTP responses, using each
exception's `error_code` to populate the standard error
envelope's "error_code" field (see app/core/exception_handlers.py
and Appendix C / Appendix B of the API design doc).

Where the design doc's Appendix C already defines a code
(AUTH_001, AUTH_005, AUTH_006, RTE_001) that code is used
verbatim. For auth-module error cases the doc's Appendix C
table doesn't cover (e.g. duplicate email/phone, unknown user,
bad OTP), a code is assigned following the same "AUTH_0xx"
convention so every error this module raises has a code, not
just the ones the doc happened to enumerate.
"""


# =====================================================
# Authentication
# =====================================================

class AuthenticationError(Exception):
    """
    Base class for authentication errors.

    error_code defaults to a generic fallback so any future
    subclass that forgets to set one still produces a valid
    (if unhelpful) code instead of crashing the error handler.
    A specific code can also be passed per-instance via the
    constructor, used for cases where the same exception class
    covers more than one doc error code (see InvalidTokenError).
    """

    error_code: str = "AUTH_000"

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class EmailAlreadyExistsError(AuthenticationError):
    """Raised when email is already registered."""
    error_code = "AUTH_007"


class PhoneAlreadyExistsError(AuthenticationError):
    """Raised when phone number is already registered."""
    error_code = "AUTH_008"


class UserNotFoundError(AuthenticationError):
    """Raised when the requested user does not exist."""
    error_code = "AUTH_009"


class InvalidCredentialsError(AuthenticationError):
    """Raised when email or password is incorrect."""
    error_code = "AUTH_001"


class EmailNotVerifiedError(AuthenticationError):
    """
    Raised when a user's account is not active.

    Doc note: Appendix C splits this into AUTH_005
    (ACCOUNT_INACTIVE — an admin deactivated the account) and
    AUTH_006 (EMAIL_NOT_VERIFIED — never verified in the first
    place). The current User model has a single is_active flag
    serving both meanings, and account deactivation isn't a
    feature that exists yet (belongs to the future Admin
    module) — so every case this exception covers today is
    genuinely "never verified," and it defaults to AUTH_006.
    Once admin deactivation exists, that code path should pass
    error_code="AUTH_005" explicitly.
    """
    error_code = "AUTH_006"


class InvalidOTPError(AuthenticationError):
    """Raised when OTP is invalid or expired."""
    error_code = "AUTH_010"


class InvalidTokenError(AuthenticationError):
    """
    Raised when a JWT is invalid.

    Defaults to AUTH_003 (TOKEN_INVALID). Call sites that
    specifically detect an *expired* token (as opposed to a
    malformed/wrong-type/revoked one) pass
    error_code="AUTH_002" explicitly, matching the doc's split
    between TOKEN_EXPIRED and TOKEN_INVALID.
    """
    error_code = "AUTH_003"


class InsufficientPermissionsError(AuthenticationError):
    """
    Raised when an authenticated user's role isn't allowed to
    access a role-restricted route. See app/dependencies/roles.py.
    """
    error_code = "AUTH_004"


class AccountAlreadyVerifiedError(AuthenticationError):
    """Raised when account is already verified."""
    error_code = "AUTH_011"


class RateLimitExceededError(AuthenticationError):
    """Raised when a rate-limited action is attempted too often."""
    error_code = "RTE_001"


class ChatSessionAccessDeniedError(AuthenticationError):
    """
    Raised when a caller tries to send a message into or read the
    history of a chat_sessions session_id that already belongs to a
    different user. Not covered by the doc's Appendix C table, so
    assigned the next AUTH_0xx code following the same convention as
    the other auth-module cases the doc doesn't enumerate.
    """
    error_code = "AUTH_012"


# =====================================================
# Complaints
# =====================================================

class ComplaintError(Exception):
    """
    Base class for complaint-domain errors, same shape and reasoning
    as AuthenticationError above (a default error_code every subclass
    inherits, overridable per-instance), just scoped to its own
    COMP_0xx code namespace instead of reusing AUTH_0xx for something
    that isn't an auth concern.
    """

    error_code: str = "COMP_000"

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class ComplaintNotFoundError(ComplaintError):
    """Raised when the requested complaint does not exist."""
    error_code = "COMP_001"


class InvalidStaffAssignmentError(ComplaintError):
    """
    Raised when assigning a complaint to a user who either doesn't
    exist or doesn't have role='staff'. Deliberately doesn't
    distinguish "no such user" from "exists but wrong role" in the
    message, an admin picking assignees from a UI wouldn't be able to
    select a citizen/admin id in the first place, so this is really
    a defense against a malformed or stale request, not a case that
    needs a finely differentiated error for a legitimate caller.
    """
    error_code = "COMP_002"


class ComplaintNotAssignableError(ComplaintError):
    """
    Raised when trying to assign a complaint that's already in a
    terminal state (resolved, closed, rejected, withdrawn) — there's
    no one left to hand it to at that point.
    """
    error_code = "COMP_003"