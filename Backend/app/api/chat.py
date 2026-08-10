from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies.auth import get_current_user
from ..dependencies.roles import require_roles
from ..model import User
from ..schemas.chat import (
    ChatFiledComplaint,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    KnowledgeBaseDocumentCreateRequest,
    KnowledgeBaseDocumentListResponse,
    KnowledgeBaseDocumentOut,
    RebuildIndexResponse,
)
from ..schemas.common import SuccessResponse
from ..services.chat_service import get_chat_history, send_chat_message
from ..services.kb_service import add_kb_document, delete_kb_document, list_kb_documents, rebuild_index
from ..utils.constants import ROLE_ADMIN

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
    second request. Only ever populated for a citizen caller, staff
    don't file complaints through this chat (see chat_service.py and
    conversation_graph.route_by_intent).
    """
    reply, complaint = await send_chat_message(
        body.session_id,
        current_user.id,
        body.message,
        db,
        body.latitude,
        body.longitude,
        user_role=current_user.role,
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


@router.get(
    "/knowledge-base",
    response_model=SuccessResponse[KnowledgeBaseDocumentListResponse],
    summary="List Nagrik Saathi's knowledge base documents (admin only)",
)
async def list_kb_documents_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Lists the static PDFs baked into app/chatbot/data (id is null,
    not deletable) alongside every admin-added document (source
    "admin", deletable via DELETE /chat/knowledge-base/{id}).
    """
    documents = await list_kb_documents(db)
    return SuccessResponse[KnowledgeBaseDocumentListResponse](
        message="Knowledge base documents retrieved.",
        data=KnowledgeBaseDocumentListResponse(
            documents=[KnowledgeBaseDocumentOut.model_validate(d) for d in documents]
        ),
    )


@router.post(
    "/knowledge-base",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[KnowledgeBaseDocumentOut],
    summary="Add a document to the knowledge base (admin only)",
)
async def add_kb_document_route(
    body: KnowledgeBaseDocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Adds a new text document to the knowledge base. Not searchable by
    the chatbot until POST /chat/rebuild-index is called, adding
    several documents before rebuilding once is fine.
    """
    document = await add_kb_document(body.title, body.content, db)
    await db.commit()

    return SuccessResponse[KnowledgeBaseDocumentOut](
        message="Knowledge base document added.",
        data=KnowledgeBaseDocumentOut(
            id=document.id, title=document.title, source="admin", created_at=document.created_at
        ),
    )


@router.delete(
    "/knowledge-base/{document_id}",
    response_model=SuccessResponse[None],
    summary="Remove a document from the knowledge base (admin only)",
)
async def delete_kb_document_route(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Raises:
        KnowledgeBaseDocumentNotFoundError: 404, if the document
            doesn't exist (this can never refer to one of the static
            PDFs, only admin-added documents are DB rows).
    """
    await delete_kb_document(document_id, db)
    await db.commit()

    return SuccessResponse[None](message="Knowledge base document deleted.")


@router.post(
    "/rebuild-index",
    response_model=SuccessResponse[RebuildIndexResponse],
    summary="Rebuild the FAISS index after knowledge base changes (admin only)",
)
async def rebuild_index_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """
    Rebuilds the FAISS index from the static PDFs plus every current
    admin-added document, and swaps it into the running chatbot
    immediately, no server restart needed. Takes a few seconds
    (embedding only, the static PDFs' OCR text is cached after the
    first rebuild of the process).
    """
    stats = await rebuild_index(db)
    return SuccessResponse[RebuildIndexResponse](
        message="Knowledge base index rebuilt.",
        data=RebuildIndexResponse(**stats),
    )
