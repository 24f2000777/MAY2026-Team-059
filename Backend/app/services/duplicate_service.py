"""
Duplicate complaint detection (#82-84).

Embeds complaint text with a local sentence-transformer model (same
model already used for the chatbot's knowledge base, all-MiniLM-L6-v2,
so no new model download) and compares it against every other
complaint's text by cosine similarity. No schema change: embeddings
aren't stored on the complaints table. Instead, computed embeddings are
kept in an in-process cache keyed by complaint id, so a complaint whose
text hasn't changed since the last check is never re-embedded, only new
or edited complaints pay the inference cost. The cache is per-process
and rebuilds itself after a restart, no schema or migration involved.
"""

import threading

import torch
from fastapi.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer, util
from sqlalchemy import select

from app.model import Complaint

DUPLICATE_SIMILARITY_THRESHOLD = 0.85

_model = None
_model_lock = threading.Lock()

# complaint_id -> (text it was last embedded from, its embedding tensor).
_embedding_cache: dict = {}


def _get_model() -> SentenceTransformer:
    """
    Lazily loads the model on first use rather than at import time (like
    app/chatbot/knowledge_base.py already does), so importing this module
    under pytest, or in a worker/process that never checks for
    duplicates, doesn't pay the load cost or hold the memory.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _complaint_text(complaint: Complaint) -> str:
    return f"{complaint.title}. {complaint.description}"


def _embed_corpus(model: SentenceTransformer, complaints: list[Complaint]) -> torch.Tensor:
    """
    Returns one embedding per complaint, in order. Reuses the cached
    embedding for any complaint whose text is unchanged since it was
    last embedded, and only runs the model on new or edited complaints.
    """
    embeddings: list = [None] * len(complaints)
    to_encode_texts = []
    to_encode_indices = []

    for i, complaint in enumerate(complaints):
        text = _complaint_text(complaint)
        cached = _embedding_cache.get(complaint.id)
        if cached is not None and cached[0] == text:
            embeddings[i] = cached[1]
        else:
            to_encode_texts.append(text)
            to_encode_indices.append(i)

    if to_encode_texts:
        fresh_embeddings = model.encode(to_encode_texts, convert_to_tensor=True)
        for idx, text, embedding in zip(to_encode_indices, to_encode_texts, fresh_embeddings):
            embeddings[idx] = embedding
            _embedding_cache[complaints[idx].id] = (text, embedding)

    return torch.stack(embeddings)


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

    model = _get_model()

    # SentenceTransformer.encode is CPU-bound and can take a moment, run
    # it in a thread so it doesn't stall the event loop for other requests
    query_embedding, corpus_embeddings = await run_in_threadpool(
        lambda: (model.encode(text, convert_to_tensor=True), _embed_corpus(model, complaints))
    )

    similarities = util.cos_sim(query_embedding, corpus_embeddings)[0]

    matches = [
        {"complaint": complaint, "similarity": float(score)}
        for complaint, score in zip(complaints, similarities)
        if float(score) >= threshold
    ]
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches
