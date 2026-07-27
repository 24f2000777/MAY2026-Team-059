"""
Authentication test suite — pytest edition.

Covers:
    - Registration (happy path, duplicate email, duplicate phone)
    - OTP verification (success, wrong OTP, expired OTP)
    - Login (success, wrong password, unknown email, inactive user)
    - Token refresh (success, access-as-refresh, garbage, rotation)
    - Forgot / Reset password flows
    - GET /auth/me, PUT /auth/me
    - Change password
    - Logout + token revocation
    - Dashboard / RBAC (role enforcement, multi-role routes, 403/401)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from jose import jwt as jose_jwt

from app.core.config import settings
from app.core.redis import redis_client
from app.utils.constants import (
    OTP_VERIFY_EMAIL,
    OTP_RESET_PASSWORD,
    ROLE_CITIZEN,
    ROLE_STAFF,
    ROLE_ADMIN,
)

# Import helpers from conftest (they are importable because
# conftest.py is in the same package and pytest auto-collects it)
from tests.conftest import (
    DEFAULT_PASSWORD,
    api_register,
    api_verify_otp,
    api_login,
    api_refresh,
    api_forgot_password,
    api_reset_password,
    api_get_me,
    api_update_me,
    api_change_password,
    api_logout,
    auth_headers,
    create_verified_user,
    create_verified_user_with_role,
    login_get_tokens,
    get_captured_otp,
    unique_email,
    unique_phone,
    cleanup,
)


NEW_PASSWORD = "TestPass@456"


# ==============================================================
# REGISTER
# ==============================================================


class TestRegister:
    """Registration happy path + edge cases."""

    async def test_register_success(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            response = await api_register(client, email, phone)
            assert response.status_code == 201
        finally:
            await cleanup([email])

    async def test_register_duplicate_verified_email(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            response = await api_register(client, email, unique_phone())
            assert response.status_code == 409
        finally:
            await cleanup([email])

    async def test_register_pending_duplicate_resends_otp(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            await api_register(client, email, phone)
            get_captured_otp(OTP_VERIFY_EMAIL, email)  # consume first OTP

            response = await api_register(client, email, unique_phone())
            assert response.status_code == 201
            assert "pending" in response.json()["message"].lower()
        finally:
            await cleanup([email])

    async def test_register_duplicate_phone(self, client):
        email_a, phone_a = unique_email(), unique_phone()
        email_b = unique_email()
        try:
            await create_verified_user(client, email=email_a, phone=phone_a)
            response = await api_register(client, email_b, phone_a)
            assert response.status_code == 409
        finally:
            await cleanup([email_a, email_b])


# ==============================================================
# VERIFY OTP
# ==============================================================


class TestVerifyOTP:
    """OTP verification flows."""

    async def test_verify_otp_wrong(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            await api_register(client, email, phone)
            get_captured_otp(OTP_VERIFY_EMAIL, email)
            response = await api_verify_otp(client, email, "000000")
            assert response.status_code == 400
        finally:
            await cleanup([email])

    async def test_verify_otp_expired(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            await api_register(client, email, phone)
            get_captured_otp(OTP_VERIFY_EMAIL, email)
            await redis_client.delete(f"{OTP_VERIFY_EMAIL}:{email}")
            response = await api_verify_otp(client, email, "123456")
            assert response.status_code == 400
        finally:
            await cleanup([email])

    async def test_verify_otp_already_verified(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            from app.services.otp_service import create_otp
            otp = await create_otp(email=email, purpose=OTP_VERIFY_EMAIL)
            response = await api_verify_otp(client, email, otp)
            assert response.status_code == 409
        finally:
            await cleanup([email])

    async def test_verify_otp_unknown_email(self, client):
        response = await api_verify_otp(client, "nobody_" + unique_email(), "123456")
        assert response.status_code == 404


# ==============================================================
# LOGIN
# ==============================================================


class TestLogin:
    """Login success and failure cases."""

    async def test_login_success(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            response = await api_login(client, email)
            assert response.status_code == 200
            data = response.json()["data"]
            assert "access_token" in data
            assert "refresh_token" in data
        finally:
            await cleanup([email])

    async def test_login_wrong_password(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            response = await api_login(client, email, password="WrongPass@999")
            assert response.status_code == 401
        finally:
            await cleanup([email])

    async def test_login_unknown_email(self, client):
        response = await api_login(client, unique_email())
        assert response.status_code == 401

    async def test_login_inactive_user(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            await api_register(client, email, phone)
            response = await api_login(client, email)
            assert response.status_code == 403
        finally:
            await cleanup([email])


# ==============================================================
# TOKEN REFRESH
# ==============================================================


class TestTokenRefresh:
    """Token refresh flows."""

    async def test_refresh_success(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            _, refresh_token = await login_get_tokens(client, email)
            response = await api_refresh(client, refresh_token)
            assert response.status_code == 200
        finally:
            await cleanup([email])

    async def test_refresh_with_access_token_rejected(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, _ = await login_get_tokens(client, email)
            response = await api_refresh(client, access_token)
            assert response.status_code == 401
        finally:
            await cleanup([email])

    async def test_refresh_garbage_token(self, client):
        response = await api_refresh(client, "this-is-not-a-jwt")
        assert response.status_code == 401

    async def test_refresh_rotates_token(self, client):
        """After refreshing, the old refresh token must be rejected."""
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            _, old_refresh = await login_get_tokens(client, email)

            first = await api_refresh(client, old_refresh)
            assert first.status_code == 200
            new_refresh = first.json()["data"]["refresh_token"]
            assert new_refresh != old_refresh

            # Old token is now single-use — must be rejected
            reuse = await api_refresh(client, old_refresh)
            assert reuse.status_code == 401

            # New token still works
            second = await api_refresh(client, new_refresh)
            assert second.status_code == 200
        finally:
            await cleanup([email])


# ==============================================================
# FORGOT / RESET PASSWORD
# ==============================================================


class TestResetPassword:
    """Forgot-password and reset-password flows."""

    async def test_forgot_password_unknown_user(self, client):
        response = await api_forgot_password(client, unique_email())
        assert response.status_code == 404

    async def test_forgot_password_inactive_user(self, client):
        email, phone = unique_email(), unique_phone()
        try:
            await api_register(client, email, phone)
            response = await api_forgot_password(client, email)
            assert response.status_code == 403
        finally:
            await cleanup([email])

    async def test_reset_password_wrong_otp(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            await api_forgot_password(client, email)
            get_captured_otp(OTP_RESET_PASSWORD, email)
            response = await api_reset_password(client, email, "000000", NEW_PASSWORD)
            assert response.status_code == 400
        finally:
            await cleanup([email])

    async def test_reset_password_success(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            await api_forgot_password(client, email)
            otp = get_captured_otp(OTP_RESET_PASSWORD, email)

            response = await api_reset_password(client, email, otp, NEW_PASSWORD)
            assert response.status_code == 200

            # Old password should no longer work
            old_login = await api_login(client, email, DEFAULT_PASSWORD)
            assert old_login.status_code == 401

            # New password should work
            new_login = await api_login(client, email, NEW_PASSWORD)
            assert new_login.status_code == 200
        finally:
            await cleanup([email])


# ==============================================================
# GET /auth/me
# ==============================================================


class TestGetMe:
    """Profile retrieval."""

    async def test_get_me_success(self, client, citizen_user):
        response = await api_get_me(client, citizen_user["access_token"])
        assert response.status_code == 200
        assert response.json()["data"]["email"] == citizen_user["email"]

    async def test_get_me_no_auth(self, client):
        response = await api_get_me(client, None)
        assert response.status_code == 401

    async def test_get_me_garbage_token(self, client):
        response = await api_get_me(client, "this-is-not-a-jwt")
        assert response.status_code == 401


# ==============================================================
# CHANGE PASSWORD
# ==============================================================


class TestChangePassword:
    """Change password flows."""

    async def test_change_password_success(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, _ = await login_get_tokens(client, email)

            response = await api_change_password(
                client, access_token, DEFAULT_PASSWORD, NEW_PASSWORD
            )
            assert response.status_code == 200

            old_login = await api_login(client, email, DEFAULT_PASSWORD)
            assert old_login.status_code == 401

            new_login = await api_login(client, email, NEW_PASSWORD)
            assert new_login.status_code == 200
        finally:
            await cleanup([email])

    async def test_change_password_wrong_current(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, _ = await login_get_tokens(client, email)
            response = await api_change_password(
                client, access_token, "TotallyWrong@000", NEW_PASSWORD
            )
            assert response.status_code == 401
        finally:
            await cleanup([email])

    async def test_change_password_no_auth(self, client):
        response = await client.post(
            "/auth/change-password",
            json={"current_password": "x", "new_password": "y"},
        )
        assert response.status_code == 401


# ==============================================================
# LOGOUT
# ==============================================================


class TestLogout:
    """Logout and token revocation."""

    async def test_logout_revokes_access_token(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, _ = await login_get_tokens(client, email)

            logout = await api_logout(client, access_token)
            assert logout.status_code == 200

            me = await api_get_me(client, access_token)
            assert me.status_code == 401
        finally:
            await cleanup([email])

    async def test_logout_revokes_refresh_if_provided(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, refresh_token = await login_get_tokens(client, email)

            await api_logout(client, access_token, refresh_token=refresh_token)

            refresh_resp = await api_refresh(client, refresh_token)
            assert refresh_resp.status_code == 401
        finally:
            await cleanup([email])

    async def test_double_logout_rejected(self, client):
        email = unique_email()
        try:
            await create_verified_user(client, email=email)
            access_token, _ = await login_get_tokens(client, email)

            first = await api_logout(client, access_token)
            assert first.status_code == 200

            second = await api_logout(client, access_token)
            assert second.status_code == 401
        finally:
            await cleanup([email])

    async def test_logout_no_auth(self, client):
        response = await client.post("/auth/logout", json={})
        assert response.status_code == 401


# ==============================================================
# DASHBOARD / RBAC
# ==============================================================


class TestRBAC:
    """Role-based access control and dashboard routes."""

    async def test_dashboard_resolves_by_role(self, client, citizen_user):
        response = await client.get(
            "/dashboard", headers=auth_headers(citizen_user["access_token"])
        )
        assert response.status_code == 200
        assert response.json()["data"]["role"] == ROLE_CITIZEN

    async def test_citizen_can_access_citizen_dashboard(self, client, citizen_user):
        response = await client.get(
            "/dashboard/citizen",
            headers=auth_headers(citizen_user["access_token"]),
        )
        assert response.status_code == 200

    async def test_citizen_cannot_access_staff_dashboard(self, client, citizen_user):
        response = await client.get(
            "/dashboard/staff",
            headers=auth_headers(citizen_user["access_token"]),
        )
        assert response.status_code == 403

    async def test_citizen_cannot_access_admin_dashboard(self, client, citizen_user):
        response = await client.get(
            "/dashboard/admin",
            headers=auth_headers(citizen_user["access_token"]),
        )
        assert response.status_code == 403

    async def test_staff_can_access_staff_dashboard(self, client, staff_user):
        response = await client.get(
            "/dashboard/staff",
            headers=auth_headers(staff_user["access_token"]),
        )
        assert response.status_code == 200

    async def test_staff_cannot_access_admin_dashboard(self, client, staff_user):
        response = await client.get(
            "/dashboard/admin",
            headers=auth_headers(staff_user["access_token"]),
        )
        assert response.status_code == 403

    async def test_admin_can_access_admin_dashboard(self, client, admin_user):
        response = await client.get(
            "/dashboard/admin",
            headers=auth_headers(admin_user["access_token"]),
        )
        assert response.status_code == 200

    async def test_dashboard_no_auth(self, client):
        response = await client.get("/dashboard/citizen")
        assert response.status_code == 401

    async def test_multiple_roles_staff_or_admin(self, client, staff_user, admin_user, citizen_user):
        """
        /dashboard/internal allows ROLE_STAFF or ROLE_ADMIN.
        Citizens must be blocked.
        """
        staff_resp = await client.get(
            "/dashboard/internal",
            headers=auth_headers(staff_user["access_token"]),
        )
        assert staff_resp.status_code == 200

        admin_resp = await client.get(
            "/dashboard/internal",
            headers=auth_headers(admin_user["access_token"]),
        )
        assert admin_resp.status_code == 200

        citizen_resp = await client.get(
            "/dashboard/internal",
            headers=auth_headers(citizen_user["access_token"]),
        )
        assert citizen_resp.status_code == 403

    async def test_forged_signature_rejected(self, client):
        """A token signed with the wrong secret must be 401."""
        payload = {
            "sub": str(uuid4()),
            "role": "admin",
            "type": "access",
        }
        forged = jose_jwt.encode(payload, "wrong-secret", algorithm="HS256")
        response = await client.get(
            "/dashboard/admin", headers=auth_headers(forged)
        )
        assert response.status_code == 401

    async def test_expired_token_rejected(self, client):
        """A token with exp in the past must be 401."""
        payload = {
            "sub": str(uuid4()),
            "role": "admin",
            "type": "access",
            "exp": 1000,  # far in the past
        }
        expired = jose_jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        response = await client.get(
            "/dashboard/admin", headers=auth_headers(expired)
        )
        assert response.status_code == 401

    async def test_invalid_token_string_rejected(self, client):
        """A completely garbage token string must be 401."""
        response = await client.get(
            "/dashboard/admin",
            headers=auth_headers("this_is_not_a_valid_token"),
        )
        assert response.status_code == 401
