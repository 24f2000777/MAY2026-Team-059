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


async def send_chat_message(session_id: str, user_id, message: str, db) -> str:
    """
    Logs the citizen's message, gets Nagrik Saathi's reply, logs that
    too, and returns the reply. Both messages are saved even though
    safe_send_message itself never raises (it has its own internal
    fallback chain), so a chat session always has a complete record.
    """
    db.add(ChatSession(session_id=session_id, user_id=user_id, role="user", message=message))

    # safe_send_message is a blocking network call (LLM API), run it in a
    # thread so it doesn't stall the event loop for other requests. The
    # surrounding db calls stay on this coroutine's own event loop.
    reply = await run_in_threadpool(safe_send_message, message, session_id)

    db.add(ChatSession(session_id=session_id, user_id=user_id, role="assistant", message=reply))
    await db.commit()

    return reply


async def get_chat_history(session_id: str, db) -> list[ChatSession]:
    """Every message in a chat session, oldest first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.session_id == session_id)
        .order_by(ChatSession.created_at)
    )
    return result.scalars().all()
