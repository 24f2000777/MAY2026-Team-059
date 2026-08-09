"""
Pytest suite for the RAG chatbot's knowledge base admin management
(#162): app/services/kb_service.py, backing GET/POST/DELETE
/chat/knowledge-base and POST /chat/rebuild-index.

Hits real Supabase, same reasoning as the other unmocked service
suites in this project. test_rebuild_index actually rebuilds the
FAISS index, the first run in a fresh process pays for OCR-ing the
static PDFs (see knowledge_base._get_static_documents), which can
take a few minutes, every call after that in the same process is
fast since the OCR'd pages are cached.
"""

import uuid

import pytest

from app.chatbot.knowledge_base import PDF_FILES, knowledge_base_index
from app.core.database import AsyncSessionLocal
from app.model import KnowledgeBaseDocument
from app.services.kb_service import (
    add_kb_document,
    delete_kb_document,
    list_kb_documents,
    rebuild_index,
)
from app.utils.exceptions import KnowledgeBaseDocumentNotFoundError


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


def _unique_title() -> str:
    return f"Pytest KB Document {uuid.uuid4()}"


class TestListKbDocuments:
    async def test_includes_the_static_pdfs(self, db):
        documents = await list_kb_documents(db)

        static_titles = {d["title"] for d in documents if d["source"] == "static"}
        assert static_titles == set(PDF_FILES)
        assert all(d["id"] is None for d in documents if d["source"] == "static")

    async def test_includes_a_newly_added_document(self, db):
        title = _unique_title()
        document = await add_kb_document(title, "Some knowledge base content for testing.", db)
        await db.commit()

        documents = await list_kb_documents(db)

        assert any(d["id"] == document.id and d["source"] == "admin" and d["title"] == title for d in documents)

        await db.delete(document)
        await db.commit()


class TestAddKbDocument:
    async def test_adds_a_document(self, db):
        title = _unique_title()
        document = await add_kb_document(title, "Content about garbage collection schedules.", db)
        await db.commit()

        assert document.id is not None
        assert document.title == title
        assert document.content == "Content about garbage collection schedules."

        await db.delete(document)
        await db.commit()


class TestDeleteKbDocument:
    async def test_deletes_an_admin_document(self, db):
        document = await add_kb_document(_unique_title(), "Content to be deleted.", db)
        await db.commit()

        await delete_kb_document(document.id, db)
        await db.commit()

        result = await db.get(KnowledgeBaseDocument, document.id)
        assert result is None

    async def test_rejects_a_nonexistent_document(self, db):
        with pytest.raises(KnowledgeBaseDocumentNotFoundError):
            await delete_kb_document(uuid.uuid4(), db)


class TestRebuildIndex:
    async def test_rebuild_includes_an_admin_documents_content(self, db):
        marker = f"UniqueMarkerToken{uuid.uuid4().hex}"
        document = await add_kb_document(
            _unique_title(), f"This test document contains {marker} as a unique searchable marker.", db
        )
        await db.commit()

        stats = await rebuild_index(db)

        assert stats["admin_document_count"] >= 1
        assert stats["chunk_count"] > 0

        results = knowledge_base_index.store.similarity_search(marker, k=3)
        assert any(marker in r.page_content for r in results)

        await delete_kb_document(document.id, db)
        await db.commit()
        # Leaves the FAISS index rebuilt with the now-deleted document
        # still baked in until the next rebuild, same as the real
        # workflow: delete, then rebuild again to actually drop it
        # from search results.
        await rebuild_index(db)
