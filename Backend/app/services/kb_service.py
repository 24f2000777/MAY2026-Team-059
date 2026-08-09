"""
Admin management of Nagrik Saathi's RAG knowledge base (#162): listing
every KB document (static PDFs plus admin-added text), adding and
removing admin-added ones, and rebuilding the FAISS index so a change
takes effect without restarting the server.
"""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.chatbot.knowledge_base import (
    PDF_FILES,
    admin_document_to_langchain_document,
    knowledge_base_index,
)
from app.model import KnowledgeBaseDocument
from app.utils.exceptions import KnowledgeBaseDocumentNotFoundError


async def list_kb_documents(db) -> list[dict]:
    """
    Every KB document: the static PDFs first (id=None, not
    deletable), then admin-added ones newest first.
    """
    static_entries = [{"id": None, "title": filename, "source": "static", "created_at": None} for filename in PDF_FILES]

    result = await db.execute(select(KnowledgeBaseDocument).order_by(KnowledgeBaseDocument.created_at.desc()))
    admin_entries = [
        {"id": doc.id, "title": doc.title, "source": "admin", "created_at": doc.created_at}
        for doc in result.scalars().all()
    ]

    return static_entries + admin_entries


async def add_kb_document(title: str, content: str, db) -> KnowledgeBaseDocument:
    """
    Adds a new admin document to the knowledge base. Does not rebuild
    the FAISS index itself, POST /chat/rebuild-index does that
    separately, so multiple documents can be added before paying for
    a rebuild.

    Does not commit, same convention as every other service in this app.
    """
    document = KnowledgeBaseDocument(title=title, content=content)
    db.add(document)
    await db.flush()
    return document


async def delete_kb_document(document_id, db) -> None:
    """
    Removes an admin-added KB document. Only admin-added documents
    are DB rows, so a nonexistent id always means either it was never
    added or it refers to one of the static PDFs.

    Raises:
        KnowledgeBaseDocumentNotFoundError: 404, if the document doesn't exist.
    """
    document = await db.get(KnowledgeBaseDocument, document_id)
    if document is None:
        raise KnowledgeBaseDocumentNotFoundError("Knowledge base document not found.")

    await db.delete(document)
    await db.flush()


async def rebuild_index(db) -> dict:
    """
    Rebuilds the FAISS index from the static PDFs (cached after the
    first OCR pass, see knowledge_base._get_static_documents) plus
    every current admin-added document, and swaps it into
    knowledge_base_index.store so the running chatbot picks it up
    immediately, no restart needed.

    Runs in a threadpool since embedding generation is CPU-bound and
    would otherwise block the event loop, same reasoning
    chat_service.send_chat_message offloads the LLM call.
    """
    result = await db.execute(select(KnowledgeBaseDocument))
    admin_docs = result.scalars().all()
    extra_documents = [admin_document_to_langchain_document(doc) for doc in admin_docs]

    await run_in_threadpool(knowledge_base_index.rebuild, extra_documents)

    return {
        "admin_document_count": len(admin_docs),
        "chunk_count": knowledge_base_index.store.index.ntotal,
    }
