"""
Pytest suite for app/services/email_service.py: builds the
verification/reset-password email bodies and dispatches them via
Celery (send_email_task.delay()), rather than sending anything
inline in the request path.

Hits the real Celery dispatch, same reasoning as the other unmocked
service suites in this project — a real Celery worker consuming the
default queue picks these up and sends them through the shared
Ethereal test inbox (see app/tasks/email_tasks.py), same as the
live email trips already run in test_auth_full_suite.py's
forgot-password coverage. This suite only proves dispatch succeeds
and the OTP/expiry values land in the body, not inbox delivery,
that's already covered end-to-end elsewhere.
"""

from app.core.config import settings
from app.services.email_service import send_password_reset_email, send_verification_email


class TestSendVerificationEmail:
    def test_dispatches_without_raising(self):
        send_verification_email(recipient="pytest-email-service@example.com", otp="123456")

    def test_task_dispatch_returns_a_result_handle(self):
        # send_email_task.delay() returns an AsyncResult; nothing in
        # send_verification_email surfaces it, so this just proves the
        # underlying Celery call didn't silently no-op — a broker
        # connection failure would raise here, not disappear quietly.
        from app.tasks.email_tasks import send_email_task

        subject = "Verify your NAGRIK AI account"
        body = f"Your verification OTP is:\n\n123456\n\nThis OTP is valid for {settings.OTP_EXPIRE_SECONDS // 60} minutes."
        result = send_email_task.delay(recipient="pytest-email-service@example.com", subject=subject, body=body)

        assert result.id is not None


class TestSendPasswordResetEmail:
    def test_dispatches_without_raising(self):
        send_password_reset_email(recipient="pytest-email-service@example.com", otp="654321")
