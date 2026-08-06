from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..model import User
from ..schemas.chat import ChatFiledComplaint, ChatHistoryResponse, ChatMessageRequest, ChatMessageResponse
from ..schemas.common import SuccessResponse
from ..services.chat_service import get_chat_history, send_chat_message

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/message")
async def send_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sends a message to Nagrik Saathi and returns its reply, logging
    both to chat_sessions. complaint is populated only on the turn
    that actually filed one (category + location both confirmed),
    letting the frontend show a filing confirmation inline without a
    second request.
    """
    reply, complaint = await send_chat_message(
        body.session_id, current_user.id, body.message, db, body.latitude, body.longitude
    )
    return SuccessResponse[ChatMessageResponse](
        message="Message sent.",
        data=ChatMessageResponse(
            session_id=body.session_id,
            reply=reply,
            complaint=ChatFiledComplaint.model_validate(complaint) if complaint else None,
        ),
    )


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns every message in a chat session, in order, scoped to the caller's own sessions."""
    messages = await get_chat_history(session_id, current_user.id, db)
    return SuccessResponse[ChatHistoryResponse](
        message="Chat history retrieved.",
        data=ChatHistoryResponse(
            session_id=session_id,
            messages=[
                {"role": m.role, "message": m.message, "created_at": m.created_at}
                for m in messages
            ],
        ),
    )
