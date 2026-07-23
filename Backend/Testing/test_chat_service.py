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

from app.core.database import AsyncSessionLocal
from app.model import ChatSession, User
from app.services.chat_service import get_chat_history, send_chat_message


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


class TestChatService:
    async def test_send_message_persists_both_sides_of_the_conversation(self, db, citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"

        reply = await send_chat_message(
            session_id, citizen.id, "There's a pothole near Andheri station", db
        )

        assert isinstance(reply, str) and len(reply) > 0

        history = await get_chat_history(session_id, db)
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

        history = await get_chat_history(session_id, db)
        assert len(history) == 4
        timestamps = [h.created_at for h in history]
        assert timestamps == sorted(timestamps)
        assert [h.role for h in history] == ["user", "assistant", "user", "assistant"]

        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_empty_history_for_an_unknown_session(self, db):
        history = await get_chat_history(f"pytest-nonexistent-{uuid.uuid4()}", db)
        assert history == []

    async def test_two_sessions_do_not_leak_into_each_other(self, db, citizen):
        session_a = f"pytest-session-{uuid.uuid4()}"
        session_b = f"pytest-session-{uuid.uuid4()}"

        await send_chat_message(session_a, citizen.id, "Message in session A", db)
        await send_chat_message(session_b, citizen.id, "Message in session B", db)

        history_a = await get_chat_history(session_a, db)
        history_b = await get_chat_history(session_b, db)

        assert len(history_a) == 2
        assert len(history_b) == 2
        assert history_a[0].message == "Message in session A"
        assert history_b[0].message == "Message in session B"

        for h in history_a + history_b:
            await db.delete(h)
        await db.commit()
