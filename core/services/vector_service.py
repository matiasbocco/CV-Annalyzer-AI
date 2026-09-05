"""
ChromaDB wrapper for the CV bank vector store.

Design choices:
- All functions are synchronous because ChromaDB's Python client is sync.
  Callers running inside async FastAPI handlers must wrap them with
  asyncio.to_thread() to avoid blocking the event loop.
- We always pass PRE-COMPUTED embeddings to ChromaDB (never let ChromaDB call
  the OpenAI API itself).  This keeps all embedding generation in one place
  (embedding_service.py) using the shared async client, and avoids having a
  second synchronous OpenAI client hidden inside ChromaDB.
- The collection uses cosine similarity ("hnsw:space": "cosine") because CV
  text embeddings are direction-sensitive; cosine normalises for document
  length so a short executive summary and a long CV with the same skills score
  similarly.
- The embedding is stored BOTH here (for fast ANN search) AND as JSON in the
  MySQL cv row (as a backup).  If ChromaDB needs to be rebuilt — corruption,
  migration to a different vector DB, schema change — we can re-populate it
  from MySQL without re-calling the OpenAI API.
"""

import logging
from typing import Optional

from core.config import settings

log = logging.getLogger(__name__)

_chroma_client = None
_collection = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb  # deferred so startup doesn't fail if chromadb is missing
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
        _collection = _chroma_client.get_or_create_collection(
            name="cv_bank",
            metadata={"hnsw:space": "cosine"},
        )
        log.info("ChromaDB collection 'cv_bank' ready.")
    except Exception as exc:
        log.error("ChromaDB initialisation failed: %s", exc)
        _collection = None
    return _collection


def add_cv(
    cv_id: str,
    text: str,
    embedding: list[float],
    metadata: dict,
) -> None:
    """Add or replace a CV in the vector store."""
    col = _get_collection()
    if col is None:
        return
    try:
        col.upsert(
            ids=[cv_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
    except Exception as exc:
        log.error("ChromaDB add_cv failed for %s: %s", cv_id, exc)


def search_similar(
    query_embedding: list[float],
    n_results: int = 5,
    where_filter: Optional[dict] = None,
) -> list[dict]:
    """Return up to n_results CVs most similar to query_embedding.

    where_filter uses ChromaDB's operator syntax, e.g.:
        {"is_expired": {"$eq": False}}

    Returns list of {"cv_id": str, "distance": float, "metadata": dict}.
    """
    col = _get_collection()
    if col is None:
        return []
    try:
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["distances", "metadatas"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = col.query(**kwargs)
        output = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for cv_id, dist, meta in zip(ids, distances, metadatas):
            output.append({"cv_id": cv_id, "distance": dist, "metadata": meta or {}})
        return output
    except Exception as exc:
        log.error("ChromaDB search_similar failed: %s", exc)
        return []


def update_metadata(cv_id: str, metadata: dict) -> None:
    """Merge new key-value pairs into the stored metadata for cv_id."""
    col = _get_collection()
    if col is None:
        return
    try:
        col.update(ids=[cv_id], metadatas=[metadata])
    except Exception as exc:
        log.error("ChromaDB update_metadata failed for %s: %s", cv_id, exc)


def remove_cv(cv_id: str) -> None:
    """Delete a CV from the vector store."""
    col = _get_collection()
    if col is None:
        return
    try:
        col.delete(ids=[cv_id])
    except Exception as exc:
        log.error("ChromaDB remove_cv failed for %s: %s", cv_id, exc)
