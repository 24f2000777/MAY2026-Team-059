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


class InvalidStatusTransitionError(ComplaintError):
    """
    Raised when a status transition (approve/reject/start/resolve) is
    attempted from a complaint status that doesn't allow it, e.g.
    trying to /start a complaint that's still "submitted" (not yet
    approved) or resolving one that's already "resolved".
    """
    error_code = "COMP_004"


class ComplaintNotAssignedToUserError(ComplaintError):
    """
    Raised when a staff member tries to /start or /resolve a
    complaint that isn't assigned to them. Admins bypass this check
    entirely (an admin can act on any complaint regardless of who
    it's assigned to), this only restricts staff to their own work.
    """
    error_code = "COMP_005"


class ComplaintNotOwnerError(ComplaintError):
    """
    Raised when a citizen requests GET /complaints or
    GET /complaints/{id} and tries to view a complaint that isn't
    their own. Staff and admin bypass this check entirely, it only
    restricts citizens to their own complaints, matching the same
    boundary GET /complaints/mine already enforces by construction.
    """
    error_code = "COMP_006"


class RatingAlreadyExistsError(ComplaintError):
    """
    Raised when POST /complaints/{id}/feedback is called on a
    complaint that already has a rating, ratings.complaint_id is
    unique (one rating per complaint, see app/model.py's Rating
    table), so a resubmission is always a conflict, never an update.
    """
    error_code = "COMP_007"


class ComplaintNotResolvedError(ComplaintError):
    """
    Raised when feedback is submitted for a complaint that isn't
    currently RESOLVED, the only status the design doc allows
    feedback from (submitting feedback then auto-transitions it to
    CLOSED, see feedback_service.py).
    """
    error_code = "COMP_008"


# =====================================================
# Complaint Attachments
#
# FILE_001/FILE_002 use the exact codes the API design doc's
# Appendix C already assigned them. FILE_003 (too many attachments)
# isn't in the doc's table, assigned the next FILE_00x code following
# the same convention as every other module's undocumented cases.
# =====================================================

class AttachmentError(Exception):
    """
    Base class for attachment-domain errors, same shape as
    ComplaintError/AuthenticationError above.
    """

    error_code: str = "FILE_000"

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class FileTooLargeError(AttachmentError):
    """Raised when an uploaded file exceeds settings.MAX_UPLOAD_SIZE_BYTES."""
    error_code = "FILE_001"


class UnsupportedFileTypeError(AttachmentError):
    """Raised when an uploaded file's content type isn't JPG/PNG/PDF/DOC/DOCX."""
    error_code = "FILE_002"


class TooManyAttachmentsError(AttachmentError):
    """
    Raised when a complaint already has
    settings.MAX_ATTACHMENTS_PER_COMPLAINT attachments and another
    upload is attempted.
    """
    error_code = "FILE_003"


class AttachmentNotFoundError(AttachmentError):
    """Raised when the requested attachment does not exist."""
    error_code = "FILE_004"


class NotificationError(Exception):
    """
    Base class for notification-domain errors, same shape as
    ComplaintError/AttachmentError above.
    """

    error_code: str = "NOTIF_000"

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class NotificationNotFoundError(NotificationError):
    """
    Raised when the requested notification doesn't exist, or exists
    but belongs to a different user (same 404, not 403, so a caller
    can't use this endpoint to probe whether a given notification ID
    belongs to someone else).
    """
    error_code = "NOTIF_001"


# =====================================================
# Departments
# =====================================================

class DepartmentError(Exception):
    """
    Base class for department-domain errors, same shape as
    ComplaintError/AttachmentError/NotificationError above.
    """

    error_code: str = "DEPT_000"

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class DepartmentNotFoundError(DepartmentError):
    """Raised when the requested department does not exist."""
    error_code = "DEPT_001"


class DepartmentNameAlreadyExistsError(DepartmentError):
    """
    Raised when creating a department whose name collides with an
    existing one, name has a unique constraint at the DB level too,
    this just turns that into a clean 409 instead of a raw
    IntegrityError.
    """
    error_code = "DEPT_002"


class DepartmentInUseError(DepartmentError):
    """
    Raised when trying to delete a department that still has staff
    or complaints referencing it. Both FKs are nullable and have no
    ON DELETE behavior configured, so an unguarded delete would just
    fail with a DB-level IntegrityError, this gives a clearer message
    and lets the caller know why, rather than trying to interpret raw
    constraint violation text.
    """
    error_code = "DEPT_003"
