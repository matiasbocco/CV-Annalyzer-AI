"""Internal service-to-service endpoints for the ChromaDB vector store.

Why this exists:
  ChromaDB's PersistentClient writes to local disk. The backend and the
  Celery worker run as separate Railway services, each with its OWN
  volume mounted at the same path — Railway does not support mounting
  one volume on two services. Historically both processes wrote to
  their own local Chroma independently, and the two silently drifted
  apart (e.g. an admin hard-delete only removed a CV from the backend's
  volume, leaving a "ghost" vector forever in the worker's volume —
  incident from 2026-09-15).

  The fix: only the backend ever touches ChromaDB directly (via its own
  volume, kept in sync with MySQL). When core.services.vector_service
  runs inside the worker (INTERNAL_VECTOR_API_URL is set there, and
  only there), every operation is forwarded here over Railway's private
  network instead of hitting a local Chroma. This makes the backend's
  volume the single source of truth.

Auth: these are not user-facing. A shared secret (INTERNAL_API_SECRET),
identical on both services, is checked via the X-Internal-Secret header.
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from core.config import settings
from core.services import vector_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/vector", tags=["internal"], include_in_schema=False)


async def verify_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    if not x_internal_secret or x_internal_secret != settings.internal_api_secret:
        raise HTTPException(status_code=403, detail="Invalid internal secret.")


class AddCvRequest(BaseModel):
    cv_id: str
    text: str
    embedding: list[float]
    metadata: dict


@router.post("/add", dependencies=[Depends(verify_internal_secret)])
async def internal_add_cv(body: AddCvRequest):
    await asyncio.to_thread(
        vector_service.add_cv, body.cv_id, body.text, body.embedding, body.metadata
    )
    return {"status": "ok"}


class RemoveCvRequest(BaseModel):
    cv_id: str


@router.post("/remove", dependencies=[Depends(verify_internal_secret)])
async def internal_remove_cv(body: RemoveCvRequest):
    await asyncio.to_thread(vector_service.remove_cv, body.cv_id)
    return {"status": "ok"}


class UpdateMetadataRequest(BaseModel):
    cv_id: str
    metadata: dict


@router.post("/update-metadata", dependencies=[Depends(verify_internal_secret)])
async def internal_update_metadata(body: UpdateMetadataRequest):
    await asyncio.to_thread(vector_service.update_metadata, body.cv_id, body.metadata)
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query_embedding: list[float]
    n_results: int = 5
    where_filter: dict | None = None


@router.post("/search", dependencies=[Depends(verify_internal_secret)])
async def internal_search_similar(body: SearchRequest):
    results = await asyncio.to_thread(
        vector_service.search_similar, body.query_embedding, body.n_results, body.where_filter
    )
    return {"results": results}
