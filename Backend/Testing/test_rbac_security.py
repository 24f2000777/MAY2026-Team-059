"""
RBAC Security Audit - Attacker Perspective Tests

Tests the role-based route protection against malicious inputs,
validating the 5-Step Security Audit requirements.
"""

import asyncio
import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from jose import jwt as jose_jwt

from app.main import app
from app.core.config import settings
from app.core.redis import redis_client

from test_auth_full_suite import (
    create_verified_user,
    create_verified_user_with_role,
    login_get_tokens,
    cleanup,
    expect_status,
    unique_email,
    auth_headers,
    passed,
    failed,
    PASSED,
    FAILED,
)

def craft_malicious_token(payload: dict, secret: str = settings.SECRET_KEY) -> str:
    return jose_jwt.encode(payload, secret, algorithm=settings.ALGORITHM)


async def test_rbac_forged_signature(client):
    print("\n======================================================================")
    print("ATTACKER PERSPECTIVE — Forged Signature on JWT")
    print("======================================================================")
    
    email = unique_email()
    try:
        await create_verified_user(client, email=email)
        # Create a token that looks like an admin token, but signed with wrong secret
        payload = {
            "sub": str(uuid4()),
            "role": "admin",
            "type": "access"
        }
        forged_token = craft_malicious_token(payload, secret="wrong_secret_key_1234567890123456")
        
        response = await client.get("/dashboard/admin", headers=auth_headers(forged_token))
        expect_status(response, 401, "Admin dashboard access with forged signature")
    finally:
        await cleanup([email])


async def test_rbac_tampered_payload_but_wrong_signature(client):
    print("\n======================================================================")
    print("ATTACKER PERSPECTIVE — Tampered Payload (e.g., escalating role)")
    print("======================================================================")
    # Even if they change the role to admin, if they don't have the secret, it fails.
    payload = {
        "sub": str(uuid4()),
        "role": "admin",
        "type": "access"
    }
    forged_token = craft_malicious_token(payload, secret="attacker_knows_no_secret")
    response = await client.get("/dashboard/admin", headers=auth_headers(forged_token))
    expect_status(response, 401, "Admin dashboard access with tampered payload")


async def test_rbac_insufficient_permissions_403(client):
    print("\n======================================================================")
    print("ISSUE #26 — 403 INSUFFICIENT_PERMISSIONS for wrong role")
    print("======================================================================")
    email = unique_email()
    try:
        await create_verified_user(client, email=email) # Role defaults to citizen
        access_token, _ = await login_get_tokens(client, email)
        
        response = await client.get("/dashboard/admin", headers=auth_headers(access_token))
        expect_status(response, 403, "Citizen attempting to access Admin dashboard")
    finally:
        await cleanup([email])


async def test_rbac_multiple_roles(client):
    print("\n======================================================================")
    print("ISSUE #26 — Multiple Allowed Roles (Officer OR Admin)")
    print("======================================================================")
    
    admin_email = unique_email()
    staff_email = unique_email()
    citizen_email = unique_email()
    try:
        await create_verified_user_with_role(client, role="admin", email=admin_email)
        admin_token, _ = await login_get_tokens(client, admin_email)
        
        await create_verified_user_with_role(client, role="staff", email=staff_email)
        staff_token, _ = await login_get_tokens(client, staff_email)

        await create_verified_user(client, email=citizen_email)
        citizen_token, _ = await login_get_tokens(client, citizen_email)
        
        # /internal requires ROLE_STAFF or ROLE_ADMIN
        response_admin = await client.get("/dashboard/internal", headers=auth_headers(admin_token))
        expect_status(response_admin, 200, "Admin accessing /internal dashboard (multiple roles)")
        
        response_staff = await client.get("/dashboard/internal", headers=auth_headers(staff_token))
        expect_status(response_staff, 200, "Staff accessing /internal dashboard (multiple roles)")

        response_citizen = await client.get("/dashboard/internal", headers=auth_headers(citizen_token))
        expect_status(response_citizen, 403, "Citizen attempting to access /internal dashboard")
    finally:
        await cleanup([admin_email, staff_email, citizen_email])


async def test_rbac_token_invalid_or_expired_401(client):
    print("\n======================================================================")
    print("ISSUE #26 — 401 TOKEN_EXPIRED / TOKEN_INVALID")
    print("======================================================================")
    email = unique_email()
    try:
        await create_verified_user_with_role(client, role="admin", email=email)
        access_token, _ = await login_get_tokens(client, email)
        
        # 401 Invalid Token (malformed)
        response_invalid = await client.get("/dashboard/admin", headers=auth_headers("this_is_not_a_valid_token"))
        expect_status(response_invalid, 401, "Admin dashboard access with invalid token string")
        
        # 401 Expired Token
        payload = {
            "sub": str(uuid4()), # won't even reach DB fetch since expiry is checked first
            "role": "admin",
            "type": "access",
            "exp": 1000 # Past date
        }
        expired_token = craft_malicious_token(payload, secret=settings.SECRET_KEY)
        response_expired = await client.get("/dashboard/admin", headers=auth_headers(expired_token))
        expect_status(response_expired, 401, "Admin dashboard access with expired token")
    finally:
        await cleanup([email])


TESTS = [
    test_rbac_forged_signature,
    test_rbac_tampered_payload_but_wrong_signature,
    test_rbac_insufficient_permissions_403,
    test_rbac_multiple_roles,
    test_rbac_token_invalid_or_expired_401,
]

async def main():
    print("\n" + "=" * 70)
    print("NAGRIK AI — RBAC SECURITY AUDIT (Attacker Perspective)")
    print("=" * 70)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for index, test in enumerate(TESTS, start=1):
            try:
                await test(client)
            except Exception as exc:
                failed(f"{test.__name__} crashed")
                print(exc)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    
    import test_auth_full_suite
    print(f"Passed : {test_auth_full_suite.PASSED}")
    print(f"Failed : {test_auth_full_suite.FAILED}")

    if test_auth_full_suite.FAILED == 0:
        print("🎉 ALL SECURITY TESTS PASSED")
    else:
        print("⚠ Some tests failed.")

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
