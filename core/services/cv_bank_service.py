"""
CV bank ingestion logic.

Why ingest AFTER the Analysis row is committed (not before)?

If ingestion ran before the LLM call and the LLM failed, we'd have CV rows in
the bank that were never associated with any analysis.  While not catastrophic,
this pollutes the bank with CVs that have zero associated results and wastes
embedding API credits.  Ingesting after commit means:
  1. The ranking already succeeded — these CVs produced real results.
  2. The Analysis.id is stable and available for the CVAnalysis FK.
  3. If ingestion itself fails (embedding API down), the API response is already
     returned — the user sees results and ingestion is retried next time the
     same CV is uploaded.

Why text_hash dedup instead of filename dedup?

Filenames are meaningless (everyone names their CV "resume.pdf").  Two files
named "resume.pdf" may be completely different people, and the same person's CV
may be uploaded as "John_Smith_CV_2025.pdf" and "john_smith.pdf".  The hash
identifies the actual content, so the same CV submitted twice under different
names is correctly detected as a duplicate without re-generating embeddings or
consuming storage.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import CV
from core.services import vector_service
from core.services.contact_service import extract_contact_info
from core.services.embedding_service import compute_text_hash, generate_embedding

log = logging.getLogger(__name__)


async def ingest_cv(
    db: AsyncSession,
    filename: str,
    text_content: str,
    contact_override: dict | None = None,
) -> tuple[CV, bool]:
    """Add a CV to the bank, or update it if the content already exists.

    Returns (cv, is_new).  is_new=False means a duplicate was detected.
    """
    text_hash = compute_text_hash(text_content)

    # Dedup by text_hash — filenames are not reliable identifiers.
    existing = (
        await db.execute(select(CV).where(CV.text_hash == text_hash))
    ).scalar_one_or_none()

    if existing:
        was_expired = existing.is_expired
        existing.last_seen_at = datetime.now(timezone.utc)
        existing.times_matched += 1
        existing.is_expired = False
        # When a previously expired CV is re-uploaded, stale contact data should
        # be discarded so extraction runs fresh against the new upload.
        if was_expired:
            existing.contact_extracted_at = None
        await db.flush()

        # Keep ChromaDB metadata in sync.
        await asyncio.to_thread(
            vector_service.update_metadata,
            str(existing.id),
            {
                "last_seen_at": existing.last_seen_at.isoformat(),
                "times_matched": existing.times_matched,
                "is_expired": False,
            },
        )

        # Extract contact info if missing (first time) or after expiry reset.
        if existing.contact_extracted_at is None:
            if contact_override:
                _apply_contact_dict(existing, contact_override)
            else:
                await _extract_and_apply_contact(existing, text_content)

        return existing, False

    # New CV — generate embedding.
    embedding: list[float] | None = None
    try:
        embedding = await generate_embedding(text_content)
    except Exception as exc:
        log.warning(
            "Embedding generation failed for '%s'; CV will be stored without "
            "embedding and won't appear in similarity searches until re-embedded. "
            "Error: %s",
            filename,
            exc,
        )

    now = datetime.now(timezone.utc)
    cv = CV(
        filename=filename,
        text_content=text_content,
        text_hash=text_hash,
        embedding=embedding,
        times_matched=1,
        last_seen_at=now,
        is_expired=False,
    )
    db.add(cv)
    await db.flush()  # Ensure cv.id is populated before ChromaDB call.

    if embedding is not None:
        metadata = {
            "filename": filename,
            "text_hash": text_hash,
            "last_seen_at": now.isoformat(),
            "is_expired": False,
            "times_matched": 1,
            "created_at": now.isoformat(),
        }
        await asyncio.to_thread(
            vector_service.add_cv,
            str(cv.id),
            text_content,
            embedding,
            metadata,
        )

    # Extract contact info for new CVs (or use user-supplied override).
    if contact_override:
        _apply_contact_dict(cv, contact_override)
    else:
        await _extract_and_apply_contact(cv, text_content)

    return cv, True


def _apply_contact_dict(cv: CV, contact: dict) -> None:
    """Write contact dict fields onto a CV row and stamp the timestamp."""
    cv.full_name            = contact.get("full_name")
    cv.email                = contact.get("email")
    cv.phone                = contact.get("phone")
    cv.linkedin_url         = contact.get("linkedin_url")
    cv.github_url           = contact.get("github_url")
    cv.portfolio_url        = contact.get("portfolio_url")
    cv.location             = contact.get("location")
    cv.availability         = contact.get("availability")
    cv.contact_extracted_at = datetime.now(timezone.utc)


async def _extract_and_apply_contact(cv: CV, text_content: str) -> None:
    """Call the contact extraction LLM and write results back to the CV row.

    Best-effort: any failure is logged and silently ignored so callers are
    never blocked by a contact-extraction error.
    """
    try:
        contact = await extract_contact_info(text_content)
        if not contact:
            return
        cv.full_name             = contact.get("full_name")
        cv.email                 = contact.get("email")
        cv.phone                 = contact.get("phone")
        cv.linkedin_url          = contact.get("linkedin_url")
        cv.github_url            = contact.get("github_url")
        cv.portfolio_url         = contact.get("portfolio_url")
        cv.location              = contact.get("location")
        cv.availability          = contact.get("availability")
        cv.contact_extracted_at  = datetime.now(timezone.utc)
    except Exception as exc:
        log.warning(
            "Contact extraction failed for CV '%s': %s",
            getattr(cv, "filename", "?"),
            exc,
        )


async def update_bank_cv_seen(db: AsyncSession, cv: CV) -> None:
    """Increment times_matched and refresh last_seen_at for a bank CV that was
    pulled into an analysis (not freshly uploaded)."""
    cv.last_seen_at = datetime.now(timezone.utc)
    cv.times_matched += 1
    await db.flush()
    await asyncio.to_thread(
        vector_service.update_metadata,
        str(cv.id),
        {
            "last_seen_at": cv.last_seen_at.isoformat(),
            "times_matched": cv.times_matched,
        },
    )
