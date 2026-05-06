"""Celery tasks for async CV analysis.

Design notes
------------
PDF extraction is intentionally synchronous in FastAPI (before queuing) because:
- It is CPU-bound and fast (no network I/O), so it doesn't block the event loop.
- Failing early on a bad file (before queuing) gives the user instant feedback
  instead of a silent failure 30 seconds later.
- It keeps the task payload small: only extracted text travels through Redis,
  not raw binary files.

asyncio.run() inside each task creates a fresh event loop in the Celery worker
process (which has no running loop of its own). This lets us reuse all existing
async services (LLM, DB, vector search) without rewriting them for sync.

task_acks_late=True (set in celery_app.py) means the task is acknowledged only
after it completes. If the worker crashes mid-task, the task goes back to the
queue and is retried by another worker — no silent data loss.

worker_prefetch_multiplier=1 (set in celery_app.py) means each worker picks up
one task at a time. LLM calls can take 30+ seconds and consume significant
memory; prefetching more would starve running tasks.

pymysql vs aiomysql: FastAPI uses aiomysql (async) because it runs inside an
event loop. Celery tasks are sync functions, so they use asyncio.run() to bridge
into async code. The async engine (aiomysql) is still used inside that
asyncio.run() block — the sync_engine in database.py is a documented fallback
for simple sync checks that don't need the full async pipeline.
"""

import asyncio
import uuid

from sqlalchemy import select

from core.celery_app import celery_app
from core.config import settings
from core.db.database import AsyncSessionLocal
from core.db.models import CV, Analysis, CVAnalysis
from core.models.response import (
    AnalyzeResponse,
    CandidateRanking,
    CategoryInfo,
    CandidateRankingWithSource,
    ContactInfo,
)
from core.services import vector_service
from core.services.anonymization_service import anonymize_cvs
from core.services.category_service import get_or_create_category
from core.services.cv_bank_service import ingest_cv, update_bank_cv_seen
from core.services.embedding_service import compute_text_hash, generate_embedding
from core.services.llm_service import client as llm_client
from core.services.llm_service import rank_candidates
from core.services.recency_service import compute_recency_factor, nivel_from_score


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_contact(cv) -> ContactInfo | None:
    if cv is None:
        return None
    info = ContactInfo(
        full_name=cv.full_name,
        email=cv.email,
        phone=cv.phone,
        linkedin_url=cv.linkedin_url,
        github_url=cv.github_url,
        portfolio_url=cv.portfolio_url,
        location=cv.location,
        availability=cv.availability,
    )
    if all(v is None for v in info.model_dump().values()):
        return None
    return info


def _enrich_candidate(
    candidate: CandidateRanking,
    source: str,
    recency_factor: float = 1.0,
) -> CandidateRankingWithSource:
    raw_score = candidate.score
    adjusted = max(0, min(100, round(raw_score * recency_factor)))
    return CandidateRankingWithSource(
        filename=candidate.filename,
        score=adjusted,
        original_score=raw_score if recency_factor < 1.0 else None,
        nivel=nivel_from_score(adjusted),
        detailed_scores=candidate.detailed_scores,
        strengths=candidate.strengths,
        gaps=candidate.gaps,
        recommendations=candidate.recommendations,
        summary=candidate.summary,
        source=source,
        recency_factor_applied=recency_factor,
    )


async def _search_bank(
    job_embedding: list[float],
    uploaded_hashes: set[str],
    n_results: int,
    db,
) -> list[CV]:
    raw = await asyncio.to_thread(
        vector_service.search_similar,
        job_embedding,
        n_results + len(uploaded_hashes),
        {"is_expired": {"$eq": False}},
    )
    cv_ids = [
        uuid.UUID(r["cv_id"])
        for r in raw
        if r["metadata"].get("text_hash") not in uploaded_hashes
    ][:n_results]
    if not cv_ids:
        return []
    rows = (await db.execute(select(CV).where(CV.id.in_(cv_ids)))).scalars().all()
    order = {cid: i for i, cid in enumerate(cv_ids)}
    return sorted(rows, key=lambda cv: order.get(cv.id, 999))


async def _persist_cv_analyses(db, analysis_id, enriched_ranking, filename_to_cv) -> None:
    for pos, candidate in enumerate(enriched_ranking, start=1):
        cv = filename_to_cv.get(candidate.filename)
        if cv is None:
            continue
        db.add(
            CVAnalysis(
                cv_id=cv.id,
                analysis_id=analysis_id,
                score=candidate.score,
                ranking_position=pos,
                nivel=candidate.nivel,
                detailed_scores=candidate.detailed_scores.model_dump(),
                strengths=candidate.strengths,
                gaps=candidate.gaps,
                recommendations=candidate.recommendations,
                summary=candidate.summary,
                source=candidate.source,
                recency_factor_applied=candidate.recency_factor_applied,
            )
        )
    await db.commit()


# ── Async pipelines ───────────────────────────────────────────────────────────

async def _analyze_pipeline(
    cv_data: list[dict],
    job_description: str,
    include_bank: bool,
) -> dict:
    """Full analysis pipeline. cv_data carries pre-extracted {filename, text} dicts."""
    cvs = [(item["filename"], item["text"]) for item in cv_data]
    uploaded_hashes = {compute_text_hash(text) for _, text in cvs}

    async with AsyncSessionLocal() as db:
        bank_cv_records: list[CV] = []
        if include_bank:
            try:
                job_embedding = await generate_embedding(job_description)
                bank_cv_records = await _search_bank(job_embedding, uploaded_hashes, 5, db)
            except Exception:
                pass  # degrade gracefully — analysis continues with uploaded CVs only

        bank_cvs_for_llm = [
            {"filename": cv.filename, "text": cv.text_content}
            for cv in bank_cv_records
        ]

        all_for_anon = (
            [{"filename": fn, "text": text, "source": "uploaded"} for fn, text in cvs]
            + [{"filename": bk["filename"], "text": bk["text"], "source": "bank"} for bk in bank_cvs_for_llm]
        )
        anon_cvs, label_map = anonymize_cvs(all_for_anon)
        anon_uploaded = [(c["filename"], c["text"]) for c in anon_cvs if c.get("source") == "uploaded"]
        anon_bank = [{"filename": c["filename"], "text": c["text"]} for c in anon_cvs if c.get("source") == "bank"]

        result = await rank_candidates(job_description, anon_uploaded, bank_cvs=anon_bank or None)

        for candidate in result.ranking:
            candidate.filename = label_map.get(candidate.filename, candidate.filename)

        uploaded_filenames = {fn for fn, _ in cvs}
        bank_cv_by_filename = {cv.filename: cv for cv in bank_cv_records}

        enriched: list[CandidateRankingWithSource] = []
        for candidate in result.ranking:
            if candidate.filename in uploaded_filenames:
                enriched.append(_enrich_candidate(candidate, "uploaded", 1.0))
            else:
                bank_cv = bank_cv_by_filename.get(candidate.filename)
                factor = compute_recency_factor(bank_cv.created_at) if bank_cv else 1.0
                enriched.append(_enrich_candidate(candidate, "bank", factor))
        enriched.sort(key=lambda c: c.score, reverse=True)

        category = await get_or_create_category(db, job_description, llm_client)

        analysis = Analysis(
            job_description=job_description,
            ranking=[c.model_dump() for c in enriched],
            job_summary=result.job_summary,
            model_used=settings.openai_model,
            job_category_id=category.id if category else None,
            anonymized=True,
        )
        db.add(analysis)
        await db.commit()

        filename_to_cv: dict[str, CV] = {}
        try:
            for filename, text in cvs:
                cv, _ = await ingest_cv(db, filename, text)
                filename_to_cv[filename] = cv
            await db.commit()
        except Exception:
            pass

        try:
            for bank_cv in bank_cv_records:
                filename_to_cv[bank_cv.filename] = bank_cv
                await update_bank_cv_seen(db, bank_cv)
            await db.commit()
        except Exception:
            pass

        try:
            await _persist_cv_analyses(db, analysis.id, enriched, filename_to_cv)
        except Exception:
            pass

        for candidate in enriched:
            candidate.contact = _build_contact(filename_to_cv.get(candidate.filename))

        return AnalyzeResponse(
            analysis_id=analysis.id,
            ranking=enriched,
            job_summary=result.job_summary,
            category=CategoryInfo(slug=category.slug, display_name=category.display_name)
            if category else None,
            anonymized=True,
        ).model_dump(mode="json")


async def _match_pipeline(job_description: str, top_n: int) -> dict:
    """Full match-job pipeline (bank-only ranking)."""
    async with AsyncSessionLocal() as db:
        job_embedding = await generate_embedding(job_description)
        bank_cv_records = await _search_bank(job_embedding, set(), top_n, db)

        if not bank_cv_records:
            raise ValueError("No suitable candidates found in the bank.")

        bank_cvs_for_llm = [
            {"filename": cv.filename, "text": cv.text_content}
            for cv in bank_cv_records
        ]

        anon_cvs, label_map = anonymize_cvs(
            [{"filename": bk["filename"], "text": bk["text"], "source": "bank"} for bk in bank_cvs_for_llm]
        )
        anon_bank = [{"filename": c["filename"], "text": c["text"]} for c in anon_cvs]

        result = await rank_candidates(job_description, uploaded_cvs=[], bank_cvs=anon_bank)

        for candidate in result.ranking:
            candidate.filename = label_map.get(candidate.filename, candidate.filename)

        bank_cv_by_filename = {cv.filename: cv for cv in bank_cv_records}

        enriched: list[CandidateRankingWithSource] = []
        for candidate in result.ranking:
            bank_cv = bank_cv_by_filename.get(candidate.filename)
            factor = compute_recency_factor(bank_cv.created_at) if bank_cv else 1.0
            c = _enrich_candidate(candidate, "bank", factor)
            c.contact = _build_contact(bank_cv)
            enriched.append(c)
        enriched.sort(key=lambda c: c.score, reverse=True)

        category = await get_or_create_category(db, job_description, llm_client)

        analysis = Analysis(
            job_description=job_description,
            ranking=[c.model_dump() for c in enriched],
            job_summary=result.job_summary,
            model_used=settings.openai_model,
            job_category_id=category.id if category else None,
            anonymized=True,
        )
        db.add(analysis)
        await db.commit()

        filename_to_cv = {cv.filename: cv for cv in bank_cv_records}
        try:
            for bank_cv in bank_cv_records:
                await update_bank_cv_seen(db, bank_cv)
            await db.commit()
            await _persist_cv_analyses(db, analysis.id, enriched, filename_to_cv)
        except Exception:
            pass

        return AnalyzeResponse(
            analysis_id=analysis.id,
            ranking=enriched,
            job_summary=result.job_summary,
            category=CategoryInfo(slug=category.slug, display_name=category.display_name)
            if category else None,
            anonymized=True,
        ).model_dump(mode="json")


# ── Celery tasks ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def analyze_cvs_task(self, cv_data: list[dict], job_description: str, include_bank: bool) -> dict:
    """Run the full CV analysis pipeline.

    cv_data carries {filename, text} dicts — text was extracted synchronously
    in the FastAPI handler (fast, fails early, keeps binary files out of Redis).
    asyncio.run() creates a fresh event loop; the Celery worker has none of its own.
    """
    try:
        return asyncio.run(_analyze_pipeline(cv_data, job_description, include_bank))
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def match_job_task(self, job_description: str, top_n: int) -> dict:
    """Run the full match-job pipeline (bank-only ranking)."""
    try:
        return asyncio.run(_match_pipeline(job_description, top_n))
    except Exception as exc:
        raise self.retry(exc=exc)
