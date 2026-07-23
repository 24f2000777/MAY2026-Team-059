"""
Pytest suite for category prediction and department routing (#70).

Same approach as test_priority_service.py: mock the LLM calls for fast,
deterministic wiring tests, plus one unmocked test at the bottom that
hits the real Groq API to prove the whole pipeline genuinely works.

Requirements
------------
- Supabase/Postgres reachable via the DATABASE_URL in .env (all tests)
- A real GROQ_API_KEY in .env (only for the real-pipeline test)
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import Complaint, Department, User
from app.services import category_service, routing_service
from app.services.category_service import predict_category
from app.services.routing_service import (
    DEPARTMENT_SEEDS,
    route_complaint,
    seed_departments,
)
from app.utils.constants import DEPARTMENT_NAMES


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def citizen(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Citizen",
        email=f"pytest-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    await db.delete(user)
    await db.commit()


class TestDepartmentSeeds:
    def test_every_seed_name_is_in_the_fixed_list(self):
        seed_names = {name for name, _ in DEPARTMENT_SEEDS}
        assert seed_names == set(DEPARTMENT_NAMES)

    async def test_seeding_is_idempotent(self, db):
        first_run = await seed_departments(db)
        second_run = await seed_departments(db)

        assert second_run == 0  # nothing new to create the second time

        result = await db.execute(select(Department.name))
        names = [row[0] for row in result.all()]
        # no duplicates, one row per fixed department name
        assert sorted(names) == sorted(DEPARTMENT_NAMES)


class TestPredictCategory:
    async def test_falls_back_to_other_when_extraction_raises(self, monkeypatch):
        def _boom(text):
            raise RuntimeError("all providers down")

        monkeypatch.setattr(category_service, "extract_complaint_info", _boom)

        category = await predict_category("some complaint text")
        assert category == "other"

    async def test_maps_bmc_category_back_to_our_enum(self, monkeypatch):
        monkeypatch.setattr(
            category_service, "extract_complaint_info",
            lambda text: {
                "severity": "Medium",
                "complaint_category": "Street Light Failure",
                "location": None,
            },
        )

        category = await predict_category("the streetlight is broken")
        assert category == "streetlight"

    async def test_returns_other_when_llm_finds_no_genuine_complaint(self, monkeypatch):
        monkeypatch.setattr(
            category_service, "extract_complaint_info",
            lambda text: {"severity": "Medium", "complaint_category": None, "location": None},
        )

        category = await predict_category("what time does the library close")
        assert category == "other"


class TestRouteComplaint:
    async def test_falls_back_to_general_administration_when_llm_fails(
        self, monkeypatch, db, citizen
    ):
        monkeypatch.setattr(
            routing_service, "predict_department",
            lambda category, description: (_ for _ in ()).throw(RuntimeError("down")),
        )

        complaint = Complaint(
            citizen_id=citizen.id, title="Test", description="Test description.",
            category="other", location_text="Test Location",
        )
        db.add(complaint)
        await db.flush()

        department = await route_complaint(complaint, db)
        assert department is not None
        assert department.name == "General Administration Department"

        await db.delete(complaint)
        await db.commit()

    async def test_routes_to_the_department_the_llm_picks(self, monkeypatch, db, citizen):
        monkeypatch.setattr(
            routing_service, "predict_department",
            lambda category, description: "Water Supply Department",
        )

        complaint = Complaint(
            citizen_id=citizen.id, title="Test", description="Test description.",
            category="water_supply", location_text="Test Location",
        )
        db.add(complaint)
        await db.flush()

        department = await route_complaint(complaint, db)
        assert department is not None
        assert department.name == "Water Supply Department"

        await db.delete(complaint)
        await db.commit()


class TestRealPipeline:
    """No mocking, exercises the real Groq call for both category prediction
    and department routing. Needs a working GROQ_API_KEY and network access.
    """

    async def test_streetlight_complaint_routes_correctly(self, db, citizen):
        complaint = Complaint(
            citizen_id=citizen.id,
            title="Streetlight not working",
            description=(
                "The streetlight near my building on Yari Road has been out "
                "for a week, it's very dark and unsafe at night."
            ),
            category="streetlight",
            location_text="Yari Road, Versova",
        )
        db.add(complaint)
        await db.flush()

        predicted = await predict_category(f"{complaint.title}. {complaint.description}")
        assert predicted == "streetlight"

        department = await route_complaint(complaint, db)
        assert department is not None
        assert department.name == "Street Lighting & Electrical Department"

        await db.delete(complaint)
        await db.commit()
