"""
Duplicate complaint detection (#82-84).

Embeds complaint text with a local sentence-transformer model (same
model already used for the chatbot's knowledge base, all-MiniLM-L6-v2,
so no new model download) and compares it against every other
complaint's text by cosine similarity. No schema change: embeddings are
computed on the fly rather than stored on the complaints table, this
re-embeds every complaint on each check, fine at the current scale, a
real vector index (or a stored-embedding column) would be the next step
if this table grows large.
"""

from fastapi.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer, util
from sqlalchemy import select

from app.model import Complaint

# Same model already used in app/chatbot/knowledge_base.py, reusing it
# means no second model download and consistent embedding behavior
# across the app.
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

DUPLICATE_SIMILARITY_THRESHOLD = 0.85


def _complaint_text(complaint: Complaint) -> str:
    return f"{complaint.title}. {complaint.description}"


async def find_duplicates_for_text(
    text: str,
    db,
    exclude_id=None,
    threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Embeds `text` and compares it against every other complaint's own
    title+description, returning the ones at or above `threshold`
    cosine similarity, most similar first. exclude_id skips a complaint
    (its own id, when checking an existing complaint against the rest).
    """
    result = await db.execute(select(Complaint))
    complaints = [c for c in result.scalars().all() if c.id != exclude_id]

    if not complaints:
        return []

    # SentenceTransformer.encode is CPU-bound and can take a moment once
    # there are many complaints, run it in a thread so it doesn't stall
    # the event loop for other requests
    query_embedding, corpus_embeddings = await run_in_threadpool(
        lambda: (
            _model.encode(text, convert_to_tensor=True),
            _model.encode([_complaint_text(c) for c in complaints], convert_to_tensor=True),
        )
    )

    similarities = util.cos_sim(query_embedding, corpus_embeddings)[0]

    matches = [
        {"complaint": complaint, "similarity": float(score)}
        for complaint, score in zip(complaints, similarities)
        if float(score) >= threshold
    ]
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches
