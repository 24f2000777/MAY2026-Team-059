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
async def staff(db):
    user = User(
        phone=f"9{uuid.uuid4().int % 10**9:09d}",
        name="Pytest Staff",
        email=f"pytest-staff-{uuid.uuid4()}@example.com",
        role="staff",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    yield user
    # Staff never file complaints through chat (that's the whole point
    # of these tests), so no Complaint cleanup needed, unlike citizen.
    await db.delete(user)
    await db.commit()


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

        reply, complaint = await send_chat_message(
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

    async def test_a_clear_complaint_gets_filed_after_the_photo_prompt(self, db, citizen):
        # Category and location both land in one message, so the very
        # next turn is Nagrik Saathi asking about an optional photo
        # (see conversation_graph.ask_about_photo), not a filed
        # complaint yet — filing happens on the turn after that,
        # regardless of what the citizen actually says back.
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = (
            "There is a big dangerous pothole on Linking Road near Bandra station, "
            "it has been there for weeks and cars keep swerving to avoid it."
        )

        first_reply, first_filed = await send_chat_message(session_id, citizen.id, message, db)
        assert isinstance(first_reply, str) and len(first_reply) > 0
        assert first_filed is None, "filing waits for the photo-prompt turn, not this one"

        reply, filed_complaint = await send_chat_message(session_id, citizen.id, "no thanks", db)
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

        # send_chat_message must hand the same freshly-created row back to
        # its caller, this is what the /chat/message route surfaces to the
        # frontend as inline filing confirmation.
        assert filed_complaint is not None
        assert filed_complaint.id == complaint.id

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_photo_prompt_still_files_when_the_reply_is_off_topic(self, db, citizen):
        # Regression test: the photo-confirmation step used to treat
        # ANY reply as "continue", including one that was actually a
        # pivot to something else entirely, silently going ahead as if
        # that new message never happened. It should still file (the
        # complaint was already fully validated before this step), but
        # the reply now says so explicitly instead of just ignoring
        # whatever the citizen actually said.
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = (
            "There is a big dangerous pothole on Linking Road near Bandra station, "
            "it has been there for weeks and cars keep swerving to avoid it."
        )

        await send_chat_message(session_id, citizen.id, message, db)

        reply, filed_complaint = await send_chat_message(
            session_id,
            citizen.id,
            "actually, there's also a streetlight that's been broken for a month on the same road",
            db,
        )

        assert filed_complaint is not None, "the already-validated complaint must still get filed"
        assert "send that on its own" in reply, "an off-topic reply should be acknowledged, not silently dropped"

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        complaints = result.scalars().all()
        assert len(complaints) == 1

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_a_short_first_person_report_is_not_misread_as_app_help(self, db, citizen):
        # Regression test: classify_intent's single LLM call misread
        # "i want to register a pothole in andheri" as app_help in
        # production (Groq, no provider error, just a wrong call),
        # silently dropping a real complaint report instead of filing
        # it. classify_intent now cross-checks an app_help verdict
        # against extraction (a second, independent signal) before
        # trusting it, this proves a real, short, first-person report
        # like this one still reaches filing even if the classifier
        # calls it app_help.
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = "i want to register a pothole in andheri"

        first_reply, first_filed = await send_chat_message(session_id, citizen.id, message, db)
        assert isinstance(first_reply, str) and len(first_reply) > 0
        assert first_filed is None, "filing waits for the photo-prompt turn, not this one"

        reply, filed_complaint = await send_chat_message(session_id, citizen.id, "no", db)
        assert isinstance(reply, str) and len(reply) > 0
        assert filed_complaint is not None, "a real complaint report must not be silently dropped"

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        complaints = result.scalars().all()
        assert len(complaints) == 1
        assert "andheri" in complaints[0].location_text.lower()

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

    async def test_short_complaint_message_still_gets_filed(self, db, citizen):
        # Regression test: ComplaintCreate.description requires 20-1000
        # chars, but chat_service used to pass the raw citizen message
        # straight through unvalidated. A short, real complaint like
        # this one is well under 20 chars, previously the confirmation
        # reply still claimed it was logged while the Complaint row
        # silently never got created.
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = "Pothole in Bandra"
        assert len(message) < 20, "this test only proves anything if the message is short"

        await send_chat_message(session_id, citizen.id, message, db)
        # Category + location already in one message -> next turn is the
        # optional-photo prompt, filing happens the turn after that.
        reply, filed_complaint = await send_chat_message(session_id, citizen.id, "no thanks", db)
        assert isinstance(reply, str) and len(reply) > 0

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        complaints = result.scalars().all()
        assert len(complaints) == 1, (
            "a short complaint message must still result in a real Complaint row, "
            "not just a confirmation reply with nothing behind it"
        )
        assert len(complaints[0].description) >= 20
        assert filed_complaint is not None
        assert filed_complaint.id == complaints[0].id

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_downstream_failure_does_not_commit_a_half_scored_complaint(
        self, db, citizen, monkeypatch
    ):
        # Regression test: create_complaint() does db.add() + an initial
        # flush() (assigning a real id) *before* score_complaint runs, a
        # real network call that can fail (route_complaint itself is a
        # plain deterministic lookup now, it can't fail this way).
        # _file_complaint_from_chat swallows any exception from that call
        # so a hiccup there doesn't surface as a chat error — but without
        # a savepoint, the already-flushed, half-initialized Complaint
        # (priority_score=0, no department) would still get committed by
        # the request's own get_db() commit, since the swallowed
        # exception never reaches it. This forces that failure and
        # checks nothing gets left behind.
        import app.services.complaint_service as complaint_service_module

        async def _boom(*args, **kwargs):
            raise RuntimeError("simulated priority-scoring failure")

        monkeypatch.setattr(complaint_service_module, "score_complaint", _boom)

        session_id = f"pytest-session-{uuid.uuid4()}"
        message = (
            "There is a large pile of uncollected garbage rotting near Dadar market, "
            "it has been there for over a week and smells terrible."
        )

        await send_chat_message(session_id, citizen.id, message, db)
        # Category + location already in one message -> that first turn
        # is just the optional-photo prompt, the actual filing attempt
        # (and the simulated failure) happens on this second one.
        reply, filed_complaint = await send_chat_message(session_id, citizen.id, "no thanks", db)
        assert isinstance(reply, str) and len(reply) > 0
        assert filed_complaint is None, "a failed filing attempt must not return a complaint"

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        assert result.scalars().all() == [], (
            "a failure inside create_complaint() must not leave a half-scored "
            "Complaint row committed"
        )

        # all four chat messages (two user turns + two assistant replies)
        # must survive the savepoint rollback, only the complaint attempt
        # itself should be undone
        history = await get_chat_history(session_id, citizen.id, db)
        assert len(history) == 4

        for h in history:
            await db.delete(h)
        await db.commit()


class TestStaffCannotFileComplaintsViaChat:
    """
    Staff never file complaints through chat, that's a citizen-only
    flow (see conversation_graph.route_by_intent redirecting "complaint"
    intent to handle_staff_no_filing for a staff caller). Regression
    coverage for a real bug: a staff member's message that was never a
    genuine complaint report ("i want you to generate a prompt to
    register a complaint") used to get misclassified and the
    extraction step hallucinated a fake complaint (a "streetlight
    failure near Andheri" that was never mentioned anywhere) out of it.
    """

    async def test_a_genuine_complaint_shaped_message_from_staff_is_not_filed(self, db, staff):
        session_id = f"pytest-session-{uuid.uuid4()}"
        message = (
            "There is a big dangerous pothole on Linking Road near Bandra station, "
            "it has been there for weeks and cars keep swerving to avoid it."
        )

        reply, filed_complaint = await send_chat_message(
            session_id, staff.id, message, db, user_role="staff"
        )

        assert isinstance(reply, str) and len(reply) > 0
        assert filed_complaint is None

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == staff.id))
        assert result.scalars().all() == []

        history = await get_chat_history(session_id, staff.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()

    async def test_a_meta_request_about_registering_does_not_get_hallucinated_into_a_complaint(
        self, db, staff
    ):
        # This is the exact reported bug: neither message here describes
        # a real problem, but the old classify_intent prompt tagged the
        # first one as "complaint" and extraction invented a category
        # and location from nothing. Two turns, same as the original
        # report (a meta-request, then an unrelated follow-up), neither
        # should ever result in a filed complaint.
        session_id = f"pytest-session-{uuid.uuid4()}"

        first_reply, first_filed = await send_chat_message(
            session_id, staff.id, "i want you to generate a prompt to register a complaint", db, user_role="staff"
        )
        assert isinstance(first_reply, str) and len(first_reply) > 0
        assert first_filed is None

        second_reply, second_filed = await send_chat_message(
            session_id, staff.id, "i love you", db, user_role="staff"
        )
        assert isinstance(second_reply, str) and len(second_reply) > 0
        assert second_filed is None

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == staff.id))
        assert result.scalars().all() == [], (
            "no complaint should ever be filed for a staff caller, regardless of what "
            "the conversation was misclassified as"
        )

        history = await get_chat_history(session_id, staff.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()


class TestCitizenMetaRequestsDoNotHallucinateAComplaint:
    """
    Same regression as TestStaffCannotFileComplaintsViaChat, but for a
    citizen caller: a meta-request about the registration feature
    should never be misread as an actual complaint report either,
    the fix (classify_intent routing these to app_help instead of
    leaving them ambiguous) applies regardless of role.
    """

    async def test_a_meta_request_about_registering_is_not_filed_as_a_complaint(self, db, citizen):
        session_id = f"pytest-session-{uuid.uuid4()}"

        reply, filed_complaint = await send_chat_message(
            session_id, citizen.id, "i want you to generate a prompt to register a complaint", db
        )

        assert isinstance(reply, str) and len(reply) > 0
        assert filed_complaint is None, (
            "a meta-request about the registration feature is not itself a complaint "
            "report and must not get filed as one"
        )

        result = await db.execute(select(Complaint).where(Complaint.citizen_id == citizen.id))
        assert result.scalars().all() == []

        history = await get_chat_history(session_id, citizen.id, db)
        for h in history:
            await db.delete(h)
        await db.commit()
