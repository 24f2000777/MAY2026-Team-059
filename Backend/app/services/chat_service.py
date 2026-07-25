"""
Wires Nagrik Saathi (app/chatbot/conversation_graph.safe_send_message) into
the API (#77-81). The chatbot logic itself, extraction, the knowledge
base, the conversation graph, was already built on feature/rag-chatbot,
this module is the missing piece connecting it to real chat_sessions
rows instead of a CLI script.
"""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.chatbot.conversation_graph import safe_send_message
from app.model import ChatSession
from app.utils.exceptions import ChatSessionAccessDeniedError


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


async def send_chat_message(session_id: str, user_id, message: str, db) -> str:
    """
    Logs the citizen's message, gets Nagrik Saathi's reply, logs that
    too, and returns the reply. Both messages are saved even though
    safe_send_message itself never raises (it has its own internal
    fallback chain), so a chat session always has a complete record.
    """
    await _check_session_ownership(session_id, user_id, db)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="user", message=message))

    # safe_send_message is a blocking network call (LLM API), run it in a
    # thread so it doesn't stall the event loop for other requests. The
    # surrounding db calls stay on this coroutine's own event loop.
    reply = await run_in_threadpool(safe_send_message, message, session_id)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="assistant", message=reply))

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
