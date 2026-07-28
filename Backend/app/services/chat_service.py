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
from app.model import ChatSession
from app.schemas.complaint import ComplaintCreate, ComplaintLocation
from app.services.category_service import BMC_TO_OUR_CATEGORY
from app.services.complaint_service import create_complaint
from app.utils.exceptions import ChatSessionAccessDeniedError

logger = logging.getLogger(__name__)


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


async def _file_complaint_from_chat(user_id, extracted_info: dict, db) -> None:
    """
    Persists the complaint the conversation just finished extracting,
    through the same create_complaint() pipeline POST /complaints uses
    (priority scoring, department routing, high-risk flagging). Never
    raises: a citizen already got their confirmation reply from the
    bot, a problem here shouldn't turn that into a visible chat error.
    """
    bmc_category = extracted_info["complaint_category"]
    location = extracted_info["location"]
    title = f"{bmc_category} near {location}"[:100]

    try:
        data = ComplaintCreate(
            title=title,
            description=extracted_info["description"],
            category=BMC_TO_OUR_CATEGORY.get(bmc_category, "other"),
            location=ComplaintLocation(address=location),
        )
        await create_complaint(user_id, data, db)
    except Exception:
        logger.warning(
            "failed to create complaint from chat extraction for user %s",
            user_id,
            exc_info=True,
        )


async def send_chat_message(session_id: str, user_id, message: str, db) -> str:
    """
    Logs the citizen's message, gets Nagrik Saathi's reply, logs that
    too, and returns the reply. Both messages are saved even though
    the conversation graph itself never raises (it has its own internal
    fallback chain), so a chat session always has a complete record.

    If this turn's conversation finalized a complaint (category +
    location both confirmed), also creates a real Complaint row from
    it, scored and routed the same way POST /complaints does.
    """
    await _check_session_ownership(session_id, user_id, db)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="user", message=message))

    # send_message_and_extract is a blocking network call (LLM API), run
    # it in a thread so it doesn't stall the event loop for other
    # requests. The surrounding db calls stay on this coroutine's own
    # event loop.
    reply, extracted_info = await run_in_threadpool(send_message_and_extract, message, session_id)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="assistant", message=reply))

    if extracted_info is not None:
        await _file_complaint_from_chat(user_id, extracted_info, db)

    # flush, not commit: transaction boundaries belong to the get_db
    # dependency at the router layer, which commits once at the end of
    # the request.
    await db.flush()

    return reply


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
