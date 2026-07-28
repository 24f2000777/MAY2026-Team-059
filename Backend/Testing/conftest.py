"""
Shared pytest setup for everything under Testing/.

Makes `app` importable the same way test_db.py already does by hand,
just once here instead of every test file repeating the sys.path line.
Add shared fixtures (DB session, auth tokens, etc.) here as more test
files adopt pytest.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
import pytest

from app.main import app


@pytest.fixture
async def client():
    """
    Real ASGI-level HTTP client for the actual FastAPI app, no
    socket/uvicorn needed. Moved here from test_auth_full_suite.py once
    a second file (test_rbac_security.py) needed the same fixture —
    conftest.py fixtures are shared across every file under Testing/,
    a fixture defined inside one test module is not.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
