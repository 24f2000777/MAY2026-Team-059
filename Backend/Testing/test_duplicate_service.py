"""
Pytest suite for duplicate complaint detection (#82-84).

No mocking needed, unlike the LLM-backed suites: the sentence-transformer
model runs locally (no network call, no API key), so every test here
runs the real embedding model directly against real Supabase data.
"""

import uuid

import pytest

from app.core.database import AsyncSessionLocal
from app.model import Complaint, User
from app.services.duplicate_service import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    find_duplicates_for_text,
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


class TestFindDuplicatesForText:
    async def test_no_matches_when_table_has_no_complaints(self, db):
        matches = await find_duplicates_for_text("some brand new complaint text", db)
        assert matches == []

    async def test_finds_a_near_identical_complaint_above_threshold(self, db, citizen):
        original = Complaint(
            citizen_id=citizen.id,
            title="Pothole on Linking Road",
            description=(
                "There is a large dangerous pothole on Linking Road near the "
                "market, cars keep swerving to avoid it."
            ),
            category="pothole",
            location_text="Linking Road",
        )
        db.add(original)
        await db.flush()

        near_duplicate_text = (
            "Big pothole near Linking Road market. A big dangerous pothole "
            "exists on Linking Road close to the market, vehicles are "
            "swerving around it constantly."
        )
        matches = await find_duplicates_for_text(near_duplicate_text, db)

        assert len(matches) == 1
        assert matches[0]["complaint"].id == original.id
        assert matches[0]["similarity"] >= DUPLICATE_SIMILARITY_THRESHOLD

        await db.delete(original)
        await db.commit()

    async def test_unrelated_complaint_is_not_flagged(self, db, citizen):
        garbage_complaint = Complaint(
            citizen_id=citizen.id,
            title="Garbage not collected",
            description=(
                "Garbage has not been collected from my street in Dadar for "
                "over a week now, it's starting to smell."
            ),
            category="garbage",
            location_text="Dadar",
        )
        db.add(garbage_complaint)
        await db.flush()

        matches = await find_duplicates_for_text(
            "There is a dangerous pothole on my street causing accidents", db
        )
        assert matches == []

        await db.delete(garbage_complaint)
        await db.commit()

    async def test_exclude_id_omits_the_complaint_itself(self, db, citizen):
        complaint = Complaint(
            citizen_id=citizen.id,
            title="Streetlight out",
            description="The streetlight outside my building has been out for days.",
            category="streetlight",
            location_text="Test Location",
        )
        db.add(complaint)
        await db.flush()

        # checking a complaint's own text against the table, excluding itself,
        # with nothing else in the table, should find nothing
        matches = await find_duplicates_for_text(
            f"{complaint.title}. {complaint.description}", db, exclude_id=complaint.id
        )
        assert matches == []

        await db.delete(complaint)
        await db.commit()

    async def test_matches_are_sorted_most_similar_first(self, db, citizen):
        exact_reword = Complaint(
            citizen_id=citizen.id,
            title="Pothole on SV Road",
            description="A dangerous pothole has formed on SV Road near the signal, it needs urgent repair.",
            category="pothole",
            location_text="SV Road",
        )
        looser_paraphrase = Complaint(
            citizen_id=citizen.id,
            title="Road damage near SV Road",
            description="There's some road damage close to the SV Road signal area that could use attention.",
            category="road",
            location_text="SV Road",
        )
        db.add_all([exact_reword, looser_paraphrase])
        await db.flush()

        matches = await find_duplicates_for_text(
            "Dangerous pothole formed on SV Road near the signal, needs urgent repair", db
        )

        if len(matches) == 2:
            assert matches[0]["similarity"] >= matches[1]["similarity"]

        await db.delete(exact_reword)
        await db.delete(looser_paraphrase)
        await db.commit()
