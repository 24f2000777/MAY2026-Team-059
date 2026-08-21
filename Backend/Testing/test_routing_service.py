"""
Pytest suite for category prediction (#70) and department routing (#69).

Category prediction is still LLM-based (category_service), same approach
as test_priority_service.py: mock the LLM calls for fast, deterministic
wiring tests, plus one unmocked test at the bottom that hits the real
Groq API to prove the whole pipeline genuinely works.

Department routing (routing_service.route_complaint) is a plain
CATEGORY_TO_DEPARTMENT lookup now, not an LLM call, so its tests need no
mocking at all, they're exercising the real thing directly.

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
from app.schemas.complaint import ComplaintCategory
from app.services import category_service
from app.services.category_service import predict_category
from app.services.routing_service import (
    DEPARTMENT_SEEDS,
    route_complaint,
    seed_departments,
)
from app.utils.constants import CATEGORY_TO_DEPARTMENT, DEPARTMENT_NAMES


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
        # No duplicates, one row per fixed department name. This is a
        # shared database though, so don't require the table to contain
        # *only* these names, other departments can legitimately (or
        # accidentally) exist alongside the seeded ones, only assert on
        # what seeding itself actually controls.
        for fixed_name in DEPARTMENT_NAMES:
            assert names.count(fixed_name) == 1


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


class TestCategoryToDepartmentMapping:
    def test_every_category_has_a_department_mapping(self):
        # Every real ComplaintCategory value must route somewhere, this
        # would have caught the real bug that motivated the deterministic
        # rewrite: a genuine drainage complaint got LLM-routed to General
        # Administration instead of Drainage & Sewerage.
        assert set(CATEGORY_TO_DEPARTMENT.keys()) == {c.value for c in ComplaintCategory}

    def test_every_mapped_department_is_in_the_fixed_list(self):
        assert set(CATEGORY_TO_DEPARTMENT.values()) <= set(DEPARTMENT_NAMES)


class TestRouteComplaint:
    async def test_routes_every_category_to_its_mapped_department(self, db, citizen):
        for category, expected_department in CATEGORY_TO_DEPARTMENT.items():
            complaint = Complaint(
                citizen_id=citizen.id, title="Test", description="Test description.",
                category=category, location_text="Test Location",
            )
            db.add(complaint)
            await db.flush()

            department = await route_complaint(complaint, db)

            assert department is not None
            assert department.name == expected_department

            await db.delete(complaint)
            await db.commit()

    async def test_falls_back_to_general_administration_for_an_unmapped_category(
        self, db, citizen
    ):
        # Can't happen through the real API (category is schema-validated
        # against ComplaintCategory), constructed directly here to prove
        # the defensive fallback itself works.
        complaint = Complaint(
            citizen_id=citizen.id, title="Test", description="Test description.",
            category="not_a_real_category", location_text="Test Location",
        )
        db.add(complaint)
        await db.flush()

        department = await route_complaint(complaint, db)
        assert department is not None
        assert department.name == "General Administration Department"

        await db.delete(complaint)
        await db.commit()


class TestRealPipeline:
    """No mocking, exercises the real Groq call for category prediction
    (department routing itself is a plain deterministic lookup now, no LLM
    involved, see TestRouteComplaint above). Needs a working GROQ_API_KEY
    and network access.
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
