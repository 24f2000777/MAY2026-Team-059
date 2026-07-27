"""
Pytest suite for the chatbot API wiring (#77-81).

The chatbot logic itself (extraction, knowledge base, conversation graph)
was already built and evaluated on feature/rag-chatbot (see that
branch's evaluate_bot.py for the actual conversation-quality checks).
This suite covers the piece that was missing: that chat_service actually
persists both sides of a conversation to chat_sessions and returns them
in order. No mocking, hits the real Groq call, same reasoning as the
unmocked tests in the other suites, this is genuinely what needs proving.

Requirements
------------
- Supabase/Postgres reachable via the DATABASE_URL in .env
- A real GROQ_API_KEY in .env
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.model import ChatSession, Complaint, User
from app.services.chat_service import get_chat_history, send_chat_message
from app.utils.exceptions import ChatSessionAccessDeniedError


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


def _make_citizen() -> User:
    return User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Citizen",
        email=f"pytest-{uuid.uuid4()}@example.com",
        role="citizen",
        hashed_password="x",
        is_active=True,
    )


async def _delete_citizen_and_complaints(db, user):
    # Several messages in this suite ("pothole near...", "streetlight
    # out near...") read as real complaints, chat_service now actually
    # files one from those via the chatbot<->ML integration, so deleting
    # the citizen without also deleting whatever got created for them
    # would violate complaints.citizen_id's FK constraint.
    result = await db.execute(select(Complaint).where(Complaint.citizen_id == user.id))
    for complaint in result.scalars().all():
        await db.delete(complaint)
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def citizen(db):
    user = _make_citizen()
    db.add(user)
    await db.flush()
    yield user
    await _delete_citizen_and_complaints(db, user)


@pytest.fixture
async def other_citizen(db):
    user = _make_citizen()
    db.add(user)
    await db.flush()
    yield user
    await _delete_citizen_and_complaints(db, user)


class TestChatService:
    async def test_send_message_persists_both_sides_of_the_conversation(self, db, citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"

        reply = await send_chat_message(
            session_id, citizen.id, "There's a pothole near Andheri station", db
        )

        assert isinstance(reply, str) and len(reply) > 0

        history = await get_chat_history(session_id, citizen.id, db)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].message == "There's a pothole near Andheri station"
        assert history[1].role == "assistant"
        assert history[1].message == reply

        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_history_is_ordered_oldest_first_across_multiple_turns(self, db, citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"

        await send_chat_message(session_id, citizen.id, "Hi", db)
        await send_chat_message(session_id, citizen.id, "There's a streetlight out near Bandra", db)

        history = await get_chat_history(session_id, citizen.id, db)
        assert len(history) == 4
        timestamps = [h.created_at for h in history]
        assert timestamps == sorted(timestamps)
        assert [h.role for h in history] == ["user", "assistant", "user", "assistant"]

        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_empty_history_for_an_unknown_session(self, db, citizen):
        history = await get_chat_history(f"pytest-nonexistent-{uuid.uuid4()}", citizen.id, db)
        assert history == []

    async def test_two_sessions_do_not_leak_into_each_other(self, db, citizen):
        session_a = f"pytest-session-{uuid.uuid4()}"
        session_b = f"pytest-session-{uuid.uuid4()}"

        await send_chat_message(session_a, citizen.id, "Message in session A", db)
        await send_chat_message(session_b, citizen.id, "Message in session B", db)

        history_a = await get_chat_history(session_a, citizen.id, db)
        history_b = await get_chat_history(session_b, citizen.id, db)

        assert len(history_a) == 2
        assert len(history_b) == 2
        assert history_a[0].message == "Message in session A"
        assert history_b[0].message == "Message in session B"

        for h in history_a + history_b:
            await db.delete(h)
        await db.commit()

    async def test_get_chat_history_does_not_return_another_users_session(
        self, db, citizen, other_citizen
    ):
        session_id = f"pytest-session-{uuid.uuid4()}"
        await send_chat_message(session_id, citizen.id, "This is my private message", db)

        history = await get_chat_history(session_id, other_citizen.id, db)
        assert history == []

        owner_history = await get_chat_history(session_id, citizen.id, db)
        for h in owner_history:
            await db.delete(h)
        await db.commit()

    async def test_send_message_rejects_another_users_session(self, db, citizen, other_citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"
        await send_chat_message(session_id, citizen.id, "First message in my session", db)

        with pytest.raises(ChatSessionAccessDeniedError):
            await send_chat_message(session_id, other_citizen.id, "Trying to hijack this session", db)

        owner_history = await get_chat_history(session_id, citizen.id, db)
        for h in owner_history:
            await db.delete(h)
        await db.commit()


class TestChatCreatesRealComplaints:
    """
    The chatbot<->ML integration: once a conversation extracts a
    category and a specific location, chat_service should file a real
    Complaint from it (scored and routed the same way POST /complaints
    does), not just reply as if it had.
    """

    async def test_a_clear_single_turn_complaint_gets_filed(self, db, citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = (
            "There is a big dangerous pothole on Linking Road near Bandra station, "
            "it has been there for weeks and cars keep swerving to avoid it."
        )

        reply = await send_chat_message(session_id, citizen.id, message, db)
        assert isinstance(reply, str) and len(reply) > 0

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        complaints = result.scalars().all()
        assert len(complaints) == 1

        complaint = complaints[0]
        assert complaint.description == message
        assert complaint.category in {"pothole", "road", "other"}
        assert "linking road" in complaint.location_text.lower()
        assert isinstance(complaint.priority_score, int)
        assert 0 <= complaint.priority_score <= 100

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_extracted_info_does_not_leak_into_a_later_unrelated_turn(self, db, citizen):
        # Regression check for the update_state() clearing in
        # send_message_and_extract: without it, a complaint filed on
        # turn 1 would get silently re-filed (duplicated) on every
        # later turn in the same thread, since LangGraph's checkpointed
        # state persists extracted_info across turns unless cleared.
        session_id = f"pytest-session-{uuid.uuid4()}"
        complaint_message = (
            "There is a huge water leak flooding the road near Andheri station market, "
            "it has been going on for two days."
        )

        await send_chat_message(session_id, citizen.id, complaint_message, db)
        await send_chat_message(session_id, citizen.id, "thanks a lot!", db)
        await send_chat_message(session_id, citizen.id, "what is the BMC helpline number", db)

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        complaints = result.scalars().all()
        assert len(complaints) == 1

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()
