"""
Wires Nagrik Saathi (app/chatbot/conversation_graph.safe_send_message) into
the API (#77-81). The chatbot logic itself, extraction, the knowledge
base, the conversation graph, was already built on feature/rag-chatbot,
this module is the missing piece connecting it to real chat_sessions
rows instead of a CLI script.
"""

import logging

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.chatbot.conversation_graph import send_message_and_extract
from app.model import ChatSession, Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.category_service import BMC_TO_OUR_CATEGORY
from app.services.complaint_service import create_complaint
from app.utils.constants import ROLE_CITIZEN
from app.utils.exceptions import ChatSessionAccessDeniedError

logger = logging.getLogger(__name__)

# ComplaintCreate.description is 20-1000 chars. A citizen's raw chat
# message routinely falls outside that (a quick "pothole here" is
# under 20; a rambling multi-sentence message can run past 1000), so
# it can't be passed straight through unchanged.
_DESCRIPTION_MIN_LENGTH = 20
_DESCRIPTION_MAX_LENGTH = 1000


def _normalize_description(raw_message: str, bmc_category: str, location: str) -> str:
    """
    Makes the extracted description satisfy ComplaintCreate's length
    bounds without ever inventing anything that wasn't said. Too long
    is just truncated. Too short is extended with the category/location
    the conversation already confirmed, real context the citizen
    actually gave, not filler text — so the stored description stays
    truthful even for a two-word complaint.
    """
    description = raw_message.strip()

    if len(description) < _DESCRIPTION_MIN_LENGTH:
        description = f"{description} (reported via Nagrik Saathi: {bmc_category} near {location})"

    return description[:_DESCRIPTION_MAX_LENGTH]


async def _check_session_ownership(session_id: str, user_id, db) -> None:
    """
    Raises if session_id already has messages under a different
    user_id. session_id is client-chosen, so without this check one
    citizen could read or write into another citizen's session by
    guessing or otherwise obtaining its id.
    """
    existing = await db.execute(
        select(ChatSession.user_id).where(ChatSession.session_id == session_id).limit(1)
    )
    owner_id = existing.scalar_one_or_none()
    if owner_id is not None and owner_id != user_id:
        raise ChatSessionAccessDeniedError("This chat session belongs to another user.")


async def _file_complaint_from_chat(
    user_id, extracted_info: dict, db, latitude: float | None = None, longitude: float | None = None
) -> Complaint | None:
    """
    Persists the complaint the conversation just finished extracting,
    through the same create_complaint() pipeline POST /complaints uses
    (priority scoring, department routing, high-risk flagging). Never
    raises: a citizen already got their confirmation reply from the
    bot, a problem here shouldn't turn that into a visible chat error.
    Returns the created Complaint so the caller can surface it in the
    reply (or None on failure, same as if nothing had been filed).

    Runs create_complaint() inside its own savepoint (db.begin_nested)
    rather than directly in the caller's transaction. create_complaint
    does db.add() + an initial flush() (to get a real complaint id)
    *before* scoring/routing/risk-flagging run — each of those is a
    real network call (LLM/embeddings) that can fail. Without a
    savepoint, a failure there after the initial flush would still
    leave a half-initialized Complaint (priority_score=0, no
    department) sitting in the session, and since this function
    swallows the exception, the outer request's own get_db() commit
    would never know to roll it back, silently persisting a
    half-scored complaint. The savepoint scopes the rollback to just
    this attempt, leaving the two ChatSession rows already added in
    the same request untouched either way.
    """
    bmc_category = extracted_info["complaint_category"]
    location = extracted_info["location"]
    title = f"{bmc_category} near {location}"[:100]
    description = _normalize_description(extracted_info["description"], bmc_category, location)

    try:
        async with db.begin_nested():
            data = ComplaintCreate(
                title=title,
                description=description,
                category=BMC_TO_OUR_CATEGORY.get(bmc_category, "other"),
                location=ComplaintLocation(address=location, latitude=latitude, longitude=longitude),
            )
            return await create_complaint(user_id, data, db)
    except Exception:
        logger.warning(
            "failed to create complaint from chat extraction for user %s",
            user_id,
            exc_info=True,
        )
        return None


async def send_chat_message(
    session_id: str,
    user_id,
    message: str,
    db,
    latitude: float | None = None,
    longitude: float | None = None,
    user_role: str = ROLE_CITIZEN,
) -> tuple[str, Complaint | None]:
    """
    Logs the caller's message, gets Nagrik Saathi's reply, logs that
    too, and returns (reply, complaint). Both messages are saved even
    though the conversation graph itself never raises (it has its own
    internal fallback chain), so a chat session always has a complete
    record.

    If this turn's conversation finalized a complaint (category +
    location both confirmed), also creates a real Complaint row from
    it, scored and routed the same way POST /complaints does, and
    returns it alongside the reply so the route can surface it to the
    frontend. complaint is None on every turn that didn't file one.

    user_role ('citizen' or 'staff') is passed into the conversation
    graph so it can gate what the conversation is allowed to do — a
    staff caller is redirected away from complaint filing entirely
    (see conversation_graph.route_by_intent), so extracted_info should
    never come back non-None for one. The `user_role == ROLE_CITIZEN`
    check below is defense in depth on top of that graph-level gate,
    not the only thing preventing a complaint from being filed on a
    staff member's behalf.

    latitude/longitude are optional GPS coords from the chat UI's
    "share location" button. The frontend resends whatever it last
    captured on every turn, so they're just passed straight through
    to whichever turn ends up actually filing the complaint.
    """
    await _check_session_ownership(session_id, user_id, db)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="user", message=message))

    # send_message_and_extract is a blocking network call (LLM API), run
    # it in a thread so it doesn't stall the event loop for other
    # requests. The surrounding db calls stay on this coroutine's own
    # event loop.
    reply, extracted_info = await run_in_threadpool(
        send_message_and_extract, message, session_id, user_role
    )

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="assistant", message=reply))

    complaint = None
    if extracted_info is not None and user_role == ROLE_CITIZEN:
        complaint = await _file_complaint_from_chat(user_id, extracted_info, db, latitude, longitude)

    # flush, not commit: transaction boundaries belong to the get_db
    # dependency at the router layer, which commits once at the end of
    # the request.
    await db.flush()

    return reply, complaint


async def get_chat_history(session_id: str, user_id, db) -> list[ChatSession]:
    """
    Every message in a chat session, oldest first, scoped to its
    owner so one citizen can't read another's history by guessing a
    session_id.
    """
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at)
    )
    return result.scalars().all()
