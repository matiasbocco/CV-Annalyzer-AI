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

Dual-mode (local disk vs. internal HTTP) — why:

The backend and the Celery worker are separate Railway services, each with
its OWN local volume mounted at the same path. Railway cannot mount one
volume on two services, so a PersistentClient in each process necessarily
means two independent, unsynchronized Chroma stores. Historically this
caused real data drift (see incident 2026-09-15): an admin CV deletion
only reached the backend's volume, leaving a ghost vector forever in the
worker's volume, which crowded out real candidates from search results.

Fix: the backend's volume is the single source of truth. When this module
runs inside the worker (INTERNAL_VECTOR_API_URL is set — ONLY there, via
Railway env vars), every function forwards to the backend's
/internal/vector/* endpoints over Railway's private network instead of
touching local disk. When unset (local dev, and the backend itself), all
functions behave exactly as before. Every existing caller is unaffected —
the branching lives entirely inside this module.
"""

import logging
from typing import Optional

import httpx

from core.config import settings

log = logging.getLogger(__name__)

_chroma_client = None
_collection = None

_INTERNAL_TIMEOUT = 30.0


def _internal_mode() -> bool:
    return bool(settings.internal_vector_api_url)


def _internal_url(path: str) -> str:
    return f"{settings.internal_vector_api_url.rstrip('/')}{path}"


def _internal_headers() -> dict:
    return {"X-Internal-Secret": settings.internal_api_secret}


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
    if _internal_mode():
        try:
            resp = httpx.post(
                _internal_url("/internal/vector/add"),
                json={"cv_id": cv_id, "text": text, "embedding": embedding, "metadata": metadata},
                headers=_internal_headers(),
                timeout=_INTERNAL_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.error("Internal vector API add_cv failed for %s: %s", cv_id, exc)
        return

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
    if _internal_mode():
        try:
            resp = httpx.post(
                _internal_url("/internal/vector/search"),
                json={
                    "query_embedding": query_embedding,
                    "n_results": n_results,
                    "where_filter": where_filter,
                },
                headers=_internal_headers(),
                timeout=_INTERNAL_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()["results"]
        except Exception as exc:
            log.error("Internal vector API search_similar failed: %s", exc)
            return []

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
    if _internal_mode():
        try:
            resp = httpx.post(
                _internal_url("/internal/vector/update-metadata"),
                json={"cv_id": cv_id, "metadata": metadata},
                headers=_internal_headers(),
                timeout=_INTERNAL_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.error("Internal vector API update_metadata failed for %s: %s", cv_id, exc)
        return

    col = _get_collection()
    if col is None:
        return
    try:
        col.update(ids=[cv_id], metadatas=[metadata])
    except Exception as exc:
        log.error("ChromaDB update_metadata failed for %s: %s", cv_id, exc)


def remove_cv(cv_id: str) -> None:
    """Delete a CV from the vector store."""
    if _internal_mode():
        try:
            resp = httpx.post(
                _internal_url("/internal/vector/remove"),
                json={"cv_id": cv_id},
                headers=_internal_headers(),
                timeout=_INTERNAL_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            log.error("Internal vector API remove_cv failed for %s: %s", cv_id, exc)
        return

    col = _get_collection()
    if col is None:
        return
    try:
        col.delete(ids=[cv_id])
    except Exception as exc:
        log.error("ChromaDB remove_cv failed for %s: %s", cv_id, exc)
