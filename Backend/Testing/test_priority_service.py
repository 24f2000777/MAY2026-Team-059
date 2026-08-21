"""
Pytest suite for app/services/priority_service.py (issue #76).

Most tests here mock extract_complaint_info and predict_priority so they
run fast, free, and deterministic, no real LLM call or dependence on the
trained model's actual output. They exist to prove the *wiring* is
correct: the right kwargs reach predict_priority, category mapping holds
up, failures degrade safely, results persist. One test at the bottom
(TestScoreComplaintRealPipeline) intentionally does not mock anything,
it calls the real Groq API and the real trained model, to prove the
whole pipeline genuinely works end to end, the same check that was done
manually while building this feature.

Requirements
------------
- Supabase/Postgres reachable via the DATABASE_URL in .env (all tests)
- A real GROQ_API_KEY in .env (only for TestScoreComplaintRealPipeline)
"""

import uuid

import pytest

from app.core.database import AsyncSessionLocal
from app.ml.priority_scorer.formula import VALID_CATEGORIES
from app.model import Complaint, ComplaintImage, User
from app.services import priority_service
from app.services.priority_service import (
    CATEGORY_MAP,
    _get_severity,
    rescore_all_complaints,
    score_complaint,
)


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


@pytest.fixture
async def complaint(db, citizen):
    c = Complaint(
        citizen_id=citizen.id,
        title="Pytest test complaint",
        description="A test complaint description used by the pytest suite.",
        category="pothole",
        location_text="Test Location",
    )
    db.add(c)
    await db.flush()
    yield c
    await db.delete(c)
    await db.commit()


class TestCategoryMap:
    def test_every_mapped_value_is_a_valid_model_category(self):
        for our_category, bmc_category in CATEGORY_MAP.items():
            assert bmc_category in VALID_CATEGORIES, (
                f"CATEGORY_MAP['{our_category}'] = '{bmc_category}' "
                f"is not one of the model's trained categories"
            )

    def test_fallback_for_unmapped_category_is_valid(self):
        # score_complaint() falls back to this exact string via .get()'s
        # default when a category isn't in CATEGORY_MAP at all
        assert "Noise / Air Pollution" in VALID_CATEGORIES


class TestSeverityFallback:
    async def test_falls_back_to_medium_when_extraction_raises(self, monkeypatch, complaint):
        def _boom(description):
            raise RuntimeError("all providers down")

        monkeypatch.setattr(priority_service, "extract_complaint_info", _boom)

        severity = await _get_severity(complaint)
        assert severity == "Medium"


class TestScoreComplaintWiring:
    async def test_passes_mapped_category_and_severity_through(self, monkeypatch, db, complaint):
        monkeypatch.setattr(
            priority_service, "extract_complaint_info",
            lambda description: {"severity": "Critical", "complaint_category": None, "location": None},
        )

        captured = {}

        def fake_predict(features):
            captured["features"] = features
            return 77.0

        monkeypatch.setattr(priority_service, "predict_priority", fake_predict)

        score = await score_complaint(complaint, db)

        assert score == 77.0
        assert captured["features"].severity == "Critical"
        assert captured["features"].complaint_category == CATEGORY_MAP["pothole"]

    async def test_has_photo_evidence_reflects_complaint_images(self, monkeypatch, db, complaint):
        monkeypatch.setattr(
            priority_service, "extract_complaint_info",
            lambda description: {"severity": "Low", "complaint_category": None, "location": None},
        )

        captured = {}
        monkeypatch.setattr(
            priority_service, "predict_priority",
            lambda features: captured.update(features=features) or 0.0,
        )

        await score_complaint(complaint, db)
        assert captured["features"].has_photo_evidence == 0

        image = ComplaintImage(complaint_id=complaint.id, image_url="https://example.com/test.jpg")
        db.add(image)
        await db.flush()

        await score_complaint(complaint, db)
        assert captured["features"].has_photo_evidence == 1

        await db.delete(image)
        await db.commit()

    async def test_prior_complaints_and_repeat_complainant(self, monkeypatch, db, citizen, complaint):
        monkeypatch.setattr(
            priority_service, "extract_complaint_info",
            lambda description: {"severity": "Low", "complaint_category": None, "location": None},
        )
        captured = {}
        monkeypatch.setattr(
            priority_service, "predict_priority",
            lambda features: captured.update(features=features) or 0.0,
        )

        await score_complaint(complaint, db)
        assert captured["features"].prior_complaints_count == 0
        assert captured["features"].repeat_complainant == 0

        earlier = Complaint(
            citizen_id=citizen.id, title="Earlier complaint",
            description="An earlier complaint from the same citizen.",
            category="garbage", location_text="Test Location",
        )
        db.add(earlier)
        await db.flush()

        await score_complaint(complaint, db)
        assert captured["features"].prior_complaints_count == 1
        assert captured["features"].repeat_complainant == 1

        await db.delete(earlier)
        await db.commit()


class TestRescoreAllComplaints:
    async def test_updates_and_persists_every_complaint(self, monkeypatch, db, complaint):
        monkeypatch.setattr(
            priority_service, "extract_complaint_info",
            lambda description: {"severity": "Low", "complaint_category": None, "location": None},
        )
        monkeypatch.setattr(priority_service, "predict_priority", lambda features: 42.0)

        count = await rescore_all_complaints(db)
        assert count >= 1

        refreshed = await db.get(Complaint, complaint.id)
        assert refreshed.priority_score == 42


class TestScoreComplaintRealPipeline:
    """
    No mocking, exercises the real Groq call and the real trained model.
    Needs a working GROQ_API_KEY and network access. Slower and depends
    on an external service, kept separate from the fast wiring tests
    above so a missing/rate-limited key only breaks this one test.
    """

    async def test_urgent_complaint_scores_higher_than_minor_one(self, db, citizen):
        urgent = Complaint(
            citizen_id=citizen.id, title="Dangerous pothole with injury",
            description=(
                "Massive pothole on Linking Road, a scooter fell in it "
                "yesterday and the rider was hurt, extremely dangerous, "
                "needs urgent repair"
            ),
            category="pothole", location_text="Linking Road, Bandra",
        )
        minor = Complaint(
            citizen_id=citizen.id, title="Slightly loud neighbor",
            description="A bit of loud music from a neighbor, not urgent, whenever convenient",
            category="other", location_text="Andheri",
        )
        db.add_all([urgent, minor])
        await db.flush()

        urgent_score = await score_complaint(urgent, db)
        minor_score = await score_complaint(minor, db)

        assert urgent_score > minor_score

        await db.delete(urgent)
        await db.delete(minor)
        await db.commit()
