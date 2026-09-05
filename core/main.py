import asyncio
import hashlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.database import AsyncSessionLocal, get_db
from core.db.models import (
    Analysis,
    CV,
    CVAnalysis,
    Feedback,
    JobCategory,
    TiebreakerSession,
)
from core.models.response import (
    AnalyzeResponse,
    CandidateRanking,
    CandidateRankingWithSource,
    CategoryInfo,
    ContactInfo,
    ContactOverride,
)
from core.models.tiebreaker import (
    AnswerInput,
    CandidateAdjustment,
    TiebreakerAnswerRequest,
    TiebreakerAnswerResponse,
    TiebreakerCreatedResponse,
    TiebreakerNeededResponse,
    TiebreakerQuestion,
    TiebreakerSessionResponse,
)
from core.services import vector_service
from core.services.anonymization_service import anonymize_cvs
from core.services.category_service import get_or_create_category
from core.services.contact_service import extract_contact_info
from core.services.cv_bank_service import ingest_cv, update_bank_cv_seen
from core.services.embedding_service import compute_text_hash, generate_embedding
from core.services.llm_service import client as llm_client
from core.services.llm_service import rank_candidates, test_connection
from core.services.file_extraction_service import extract_text_from_bytes
from core.services.recency_service import compute_recency_factor, nivel_from_score
from core.services.tiebreaker_service import (
    apply_answers,
    detect_cluster,
    generate_questions,
)
from core.services.ttl_service import expire_old_cvs
from core.services.cleanup_service import delete_old_analyses
from core.routers.auth_router import router as auth_router
from core.routers.protected_auth_router import router as protected_auth_router
from core.routers.admin_router import router as admin_router
from core.db.models import UserRole
from core.dependencies import require_recruiter
from core.db.models import User

STATIC_DIR = Path(__file__).parent / "static"

_startup_log = __import__("logging").getLogger(__name__)

# ── Startup / shutdown ────────────────────────────────────────────────────────

async def _check_bank_drift(db: AsyncSession) -> None:
    """Warn if MySQL CV count diverges from ChromaDB vector count."""
    try:
        from sqlalchemy import func as sqlfunc
        from core.db.models import CV as _CV
        mysql_count: int = (
            await db.execute(
                select(sqlfunc.count())
                .select_from(_CV)
                .where(_CV.embedding.is_not(None), _CV.is_expired.is_(False))
            )
        ).scalar_one()

        col = await asyncio.to_thread(vector_service._get_collection)
        chroma_count = col.count() if col else 0

        if mysql_count != chroma_count:
            _startup_log.warning(
                "[bank-drift] MySQL has %d active CV(s) with embeddings but "
                "ChromaDB has %d vector(s). Run: python -m core.scripts.rebuild_chroma",
                mysql_count,
                chroma_count,
            )
        else:
            _startup_log.info("[bank-sync] OK — %d CV(s) in MySQL match ChromaDB.", mysql_count)
    except Exception as exc:
        _startup_log.warning("[bank-drift] Could not verify bank sync: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        expired = await expire_old_cvs(db)
        if expired:
            print(f"[startup] Expired {expired} stale CV(s).")
        deleted = await delete_old_analyses(db)
        if deleted:
            print(f"[startup] Deleted {deleted} analyses older than 7 days.")
        await _check_bank_drift(db)
    yield

app = FastAPI(title="CV Analyzer AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # Required for httpOnly cookies
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Register routers
app.include_router(auth_router)
app.include_router(protected_auth_router)
app.include_router(admin_router)


# ── Request bodies ────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)


# ── Shared helpers ─ contact ──────────────────────────────────────────────────

def _build_contact(cv) -> ContactInfo | None:
    """Build a ContactInfo response object from a CV ORM row.

    Returns None if the CV has no contact info at all (all fields null).
    """
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


_JD_MIN = 50
_JD_MAX = 3000
_MAX_UPLOAD_FILES = settings.max_cvs_per_analysis


class MatchJobRequest(BaseModel):
    job_description: str = Field(min_length=_JD_MIN, max_length=_JD_MAX)
    top_n: int = Field(default=10, ge=1, le=50)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _enrich_candidate(
    candidate: CandidateRanking,
    source: str,
    recency_factor: float = 1.0,
) -> CandidateRankingWithSource:
    """Apply recency factor and annotate a ranked candidate with source info."""
    raw_score = candidate.score
    adjusted = round(raw_score * recency_factor)
    adjusted = max(0, min(100, adjusted))
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
    db: AsyncSession,
) -> list[CV]:
    """Semantic search the bank, filter duplicates, return full CV records."""
    raw = await asyncio.to_thread(
        vector_service.search_similar,
        job_embedding,
        n_results + len(uploaded_hashes),  # over-fetch to absorb filtered rows
        {"is_expired": {"$eq": False}},
    )
    # Filter out CVs whose content matches one of the just-uploaded files.
    cv_ids = [
        uuid.UUID(r["cv_id"])
        for r in raw
        if r["metadata"].get("text_hash") not in uploaded_hashes
    ][:n_results]

    if not cv_ids:
        return []

    rows = (await db.execute(select(CV).where(CV.id.in_(cv_ids)))).scalars().all()
    # Preserve the ChromaDB relevance order.
    order = {cid: i for i, cid in enumerate(cv_ids)}
    return sorted(rows, key=lambda cv: order.get(cv.id, 999))


async def _persist_cv_analyses(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    enriched_ranking: list[CandidateRankingWithSource],
    filename_to_cv: dict[str, CV],
) -> None:
    """Create CVAnalysis rows for every candidate in the final ranking."""
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


# ── Static pages ──────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/test", include_in_schema=False)
def test_ui():
    return FileResponse(STATIC_DIR / "test.html")

@app.get("/match", include_in_schema=False)
def match_ui():
    return FileResponse(STATIC_DIR / "match.html")

@app.get("/upload", include_in_schema=False)
def upload_ui():
    return FileResponse(STATIC_DIR / "upload.html")

@app.get("/update", include_in_schema=False)
def update_redirect():
    return RedirectResponse("/upload", status_code=301)

@app.get("/test-llm")
async def test_llm():
    result = await test_connection()
    return {"response": result}


# ── Categories ────────────────────────────────────────────────────────────────

@app.get("/categories")
async def list_categories(
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(select(JobCategory).order_by(JobCategory.display_name))
    ).scalars().all()
    return [
        {
            "slug": c.slug,
            "display_name": c.display_name,
            "description": c.description,
            "required_skills": c.required_skills,
        }
        for c in rows
    ]


# ── Main analysis endpoint ────────────────────────────────────────────────────

@app.post("/analyze", status_code=202)
async def analyze(
    files: Annotated[list[UploadFile], File(description="One or more CV files (PDF, DOCX, JPG, PNG, WEBP)")],
    job_description: Annotated[str, Form(description="Job description text")],
    include_bank: Annotated[bool, Form(description="Merge top bank candidates into ranking")] = False,
    current_user: User = Depends(require_recruiter),
):
    # 1. Early validation (no IO needed).
    if len(files) > _MAX_UPLOAD_FILES:
        raise HTTPException(400, f"Se pueden analizar como máximo {_MAX_UPLOAD_FILES} CVs por vez.")
    jd = job_description.strip()
    if len(jd) < _JD_MIN:
        raise HTTPException(422, f"La descripción debe tener al menos {_JD_MIN} caracteres.")
    if len(jd) > _JD_MAX:
        raise HTTPException(422, f"La descripción del puesto no puede superar los {_JD_MAX} caracteres.")

    # 2. Extract text synchronously — fast, validates files early, keeps binary
    #    data out of the task queue. Only plain text travels to the Celery worker.
    cv_data: list[dict] = []
    for file in files:
        raw = await file.read()
        try:
            text = await extract_text_from_bytes(raw, file.filename or "cv")
        except HTTPException as exc:
            raise HTTPException(exc.status_code, f"{file.filename}: {exc.detail}")
        if not text.strip():
            raise HTTPException(422, f"No extractable text: {file.filename}")
        cv_data.append({"filename": file.filename, "text": text})

    # 3. Queue the heavy work (LLM ranking, DB persistence) in Celery.
    from core.tasks import analyze_cvs_task
    task = analyze_cvs_task.delay(cv_data, jd, include_bank, str(current_user.id))

    return JSONResponse({"job_id": task.id, "status": "pending"}, status_code=202)


# ── Candidate upload — Step 1: extract contact info (no DB write) ─────────────

CRITICAL_CONTACT_FIELDS = {"full_name", "email", "availability"}

@app.post("/cvs/extract-contact")
async def extract_cv_contact(
    file: Annotated[UploadFile, File(description="CV file to extract contact info from (PDF, DOCX, JPG, PNG, WEBP)")],
):
    """Extract contact info from a CV file without saving anything.

    Returns the extracted fields plus a list of critical missing fields so
    the UI can prompt the candidate to fill them before final upload.
    """
    fname = file.filename or "cv.pdf"
    raw = await file.read()
    text = await extract_text_from_bytes(raw, fname)

    if not text.strip():
        raise HTTPException(422, "No se pudo extraer texto del archivo.")

    text_hash = hashlib.sha256(raw).hexdigest()
    contact   = await extract_contact_info(text)

    missing = [f for f in CRITICAL_CONTACT_FIELDS if not contact.get(f)]

    return {
        "extracted_text_hash": text_hash,
        "extracted_contact":   contact,
        "missing_fields":      missing,
        "filename":            fname,
    }


# ── Candidate upload — Step 2: save with confirmed contact info ───────────────

@app.post("/cvs/batch")
async def upload_candidate_cv(
    files: Annotated[list[UploadFile], File(description="One or more CVs (PDF, DOCX, JPG, PNG, WEBP)")],
    contact_info: Annotated[str, Form(description="JSON contact fields (single-file flow only)")] = "{}",
    expected_hash: Annotated[str, Form(description="Hash from extract-contact step (single-file flow only)")] = "",
    db: AsyncSession = Depends(get_db),
):
    import json as _json
    import logging as _logging

    if not files:
        raise HTTPException(400, "Seleccioná al menos un archivo.")
    if len(files) > _MAX_UPLOAD_FILES:
        raise HTTPException(400, f"Se pueden subir como máximo {_MAX_UPLOAD_FILES} CVs por vez.")

    # ── Multi-file bulk mode ──────────────────────────────────────────────────
    if len(files) > 1:
        added = 0
        duplicates = 0
        failed = 0
        cv_ids: list[str] = []

        for upload_file in files:
            fname = upload_file.filename or "cv.pdf"
            try:
                raw  = await upload_file.read()
                text = await extract_text_from_bytes(raw, fname)
                if not text.strip():
                    failed += 1
                    continue
                cv, is_new = await ingest_cv(db, fname, text)
                await db.commit()
                cv_ids.append(str(cv.id))
                if is_new:
                    added += 1
                else:
                    duplicates += 1
            except Exception as exc:
                _logging.getLogger(__name__).error("Bulk CV ingest failed (%s): %s", fname, exc)
                failed += 1

        return JSONResponse(status_code=200, content={
            "added": added,
            "duplicates": duplicates,
            "failed": failed,
            "cv_ids": cv_ids,
        })

    # ── Single-file confirmed flow (2-step with contact form) ─────────────────
    file = files[0]
    fname = file.filename or "cv.pdf"
    try:
        raw  = await file.read()
        text = await extract_text_from_bytes(raw, fname)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": exc.detail if isinstance(exc.detail, str) else "No se pudo procesar el archivo.",
        })

    if not text.strip():
        return JSONResponse(status_code=400, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": "No se pudo extraer texto del archivo.",
        })

    # Hash verification — ensures the uploaded file matches the extraction step.
    actual_hash = hashlib.sha256(raw).hexdigest()
    if expected_hash and actual_hash != expected_hash:
        return JSONResponse(status_code=409, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": "El archivo no coincide con el CV analizado. "
                       "Por favor volvé al paso anterior.",
        })

    # Parse and validate contact info supplied by the candidate.
    contact_override: dict | None = None
    try:
        raw_contact = _json.loads(contact_info) if contact_info.strip() else {}
        if raw_contact:
            validated = ContactOverride.model_validate(raw_contact)
            contact_override = validated.model_dump(exclude_none=True) or None
    except Exception:
        pass  # bad JSON → fall through to LLM extraction inside ingest_cv

    try:
        cv, is_new = await ingest_cv(db, fname, text, contact_override=contact_override)
        await db.commit()
    except Exception as exc:
        _logging.getLogger(__name__).error("CV ingest failed: %s", exc)
        return JSONResponse(status_code=400, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": "Error interno al guardar el CV.",
        })

    if is_new:
        return JSONResponse(status_code=201, content={
            "status": "added", "filename": fname, "cv_id": str(cv.id),
            "message": "Tu CV fue agregado al banco exitosamente.",
        })
    return JSONResponse(status_code=200, content={
        "status": "duplicate", "filename": fname, "cv_id": str(cv.id),
        "message": "Este CV ya está en el banco.",
    })


# ── Match-job (bank-only ranking) ─────────────────────────────────────────────

@app.post("/match-job", status_code=202)
async def match_job(
    body: MatchJobRequest,
    current_user: User = Depends(require_recruiter),
):
    """Queue a bank-only CV ranking job and return a job_id immediately."""
    from core.tasks import match_job_task
    task = match_job_task.delay(body.job_description, body.top_n, str(current_user.id))
    return JSONResponse({"job_id": task.id, "status": "pending"}, status_code=202)


# ── Job status endpoints ───────────────────────────────────────────────────────

def _job_failure_message(result) -> str:
    if "No suitable candidates found in the bank" in str(result.result):
        return "Todavía no hay CVs en el banco que coincidan con esta búsqueda. Subí currículums antes de buscar candidatos."
    return "El análisis falló. Intentá de nuevo."


@app.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(require_recruiter),
):
    """Poll a queued job.  Returns HTTP 200 for all states; check the 'status' field."""
    from core.celery_app import celery_app
    result = celery_app.AsyncResult(job_id)
    state = result.state

    if state == "SUCCESS":
        return {"status": "completed", "result": result.get()}
    if state in ("FAILURE", "REVOKED"):
        return {"status": "failed", "error": _job_failure_message(result)}
    # PENDING / STARTED / RETRY — still running
    return {"status": "pending"}


@app.get("/jobs/{job_id}/result")
async def get_job_result(
    job_id: str,
    current_user: User = Depends(require_recruiter),
):
    """Convenience endpoint: returns the full result or 404/500 without polling logic."""
    from core.celery_app import celery_app
    result = celery_app.AsyncResult(job_id)
    state = result.state

    if state == "SUCCESS":
        return result.get()
    if state in ("FAILURE", "REVOKED"):
        raise HTTPException(500, _job_failure_message(result))
    raise HTTPException(404, "El análisis todavía está en proceso.")


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.post("/analyses/{analysis_id}/feedback")
async def submit_feedback(
    analysis_id: uuid.UUID,
    body: FeedbackRequest,
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(Feedback).where(Feedback.analysis_id == analysis_id))
    ).scalar_one_or_none()

    if existing:
        existing.rating = body.rating
        await db.commit()
        return JSONResponse({"updated": True}, 200)

    db.add(Feedback(analysis_id=analysis_id, rating=body.rating))
    await db.commit()
    return JSONResponse({"created": True}, 201)


# ── Tiebreaker ────────────────────────────────────────────────────────────────

@app.post("/analyses/{analysis_id}/tiebreaker")
async def start_tiebreaker(
    analysis_id: uuid.UUID,
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    analysis = (
        await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(404, "Analysis not found")

    ranking: list[dict] = analysis.ranking or []
    cluster_filenames = detect_cluster(ranking)
    if not cluster_filenames:
        return TiebreakerNeededResponse(needed=False)

    cluster_data = [c for c in ranking if c["filename"] in set(cluster_filenames)]

    try:
        questions = await generate_questions(cluster_data, llm_client)
    except Exception as e:
        raise HTTPException(502, f"Could not generate tiebreaker questions: {e}")

    session = TiebreakerSession(
        analysis_id=analysis_id,
        cluster_candidates=cluster_filenames,
        questions=[q.model_dump() for q in questions],
        status="pending",
    )
    db.add(session)
    await db.commit()

    return TiebreakerCreatedResponse(
        needed=True,
        session_id=session.id,
        cluster_candidates=cluster_filenames,
        questions=questions,
    )


@app.post("/tiebreaker/{session_id}/answer", status_code=200)
async def answer_tiebreaker(
    session_id: uuid.UUID,
    body: TiebreakerAnswerRequest,
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(
            select(TiebreakerSession).where(TiebreakerSession.id == session_id)
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(404, "Tiebreaker session not found")
    if session.status == "completed":
        raise HTTPException(409, "Session already completed")

    questions: list[dict] = session.questions
    expected_ids = {q["id"] for q in questions}
    answered_ids = {a.question_id for a in body.answers}
    if expected_ids != answered_ids:
        raise HTTPException(422, f"Must answer all questions. Expected: {sorted(expected_ids)}")

    analysis = (
        await db.execute(select(Analysis).where(Analysis.id == session.analysis_id))
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(404, "Parent analysis not found")

    cluster_set = set(session.cluster_candidates)
    cluster_data = [c for c in (analysis.ranking or []) if c["filename"] in cluster_set]
    answers_raw = [a.model_dump() for a in body.answers]
    final_ranking = apply_answers(cluster_data, questions, answers_raw)

    original_order = session.cluster_candidates
    adjustments = [
        CandidateAdjustment(
            filename=fn,
            original_position=original_order.index(fn),
            new_position=new_pos,
            moved=original_order.index(fn) - new_pos,
        )
        for new_pos, fn in enumerate(final_ranking)
    ]

    session.answers = answers_raw
    session.final_ranking = final_ranking
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return TiebreakerAnswerResponse(final_ranking=final_ranking, adjustments=adjustments)


@app.get("/tiebreaker/{session_id}")
async def get_tiebreaker(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(
            select(TiebreakerSession).where(TiebreakerSession.id == session_id)
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(404, "Tiebreaker session not found")

    return TiebreakerSessionResponse(
        session_id=session.id,
        status=session.status,
        cluster_candidates=session.cluster_candidates,
        questions=[TiebreakerQuestion.model_validate(q) for q in session.questions],
        answers=[AnswerInput(**a) for a in session.answers] if session.answers else None,
        final_ranking=session.final_ranking,
    )


# ── Analysis history ──────────────────────────────────────────────────────────

@app.get("/analyses")
async def list_analyses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of analyses for the current user (admins see all)."""
    is_admin = current_user.role == UserRole.admin

    base = select(Analysis)
    count_base = select(func.count()).select_from(Analysis)
    if not is_admin:
        base = base.where(Analysis.user_id == current_user.id)
        count_base = count_base.where(Analysis.user_id == current_user.id)

    total: int = (await db.execute(count_base)).scalar_one()
    analyses = (
        await db.execute(
            base.order_by(Analysis.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    # Batch-load categories and feedback to avoid N+1 queries.
    cat_ids = [a.job_category_id for a in analyses if a.job_category_id]
    cats: dict = {}
    if cat_ids:
        cat_rows = (
            await db.execute(select(JobCategory).where(JobCategory.id.in_(cat_ids)))
        ).scalars().all()
        cats = {c.id: c for c in cat_rows}

    analysis_ids = [a.id for a in analyses]
    feedbacks: dict = {}
    if analysis_ids:
        fb_rows = (
            await db.execute(select(Feedback).where(Feedback.analysis_id.in_(analysis_ids)))
        ).scalars().all()
        feedbacks = {fb.analysis_id: fb.rating for fb in fb_rows}

    # For admin: also resolve user emails.
    user_ids = list({a.user_id for a in analyses if a.user_id})
    user_emails: dict = {}
    if is_admin and user_ids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()
        user_emails = {u.id: u.email for u in user_rows}

    items = []
    for a in analyses:
        cat = cats.get(a.job_category_id) if a.job_category_id else None
        items.append({
            "id": str(a.id),
            "job_description_preview": a.job_description[:100],
            "job_summary_preview": (a.job_summary or "")[:150],
            "category": {"slug": cat.slug, "display_name": cat.display_name} if cat else None,
            "candidates_count": len(a.ranking) if a.ranking else 0,
            "created_at": a.created_at.isoformat(),
            "feedback_rating": feedbacks.get(a.id),
            "user_email": user_emails.get(a.user_id) if is_admin else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@app.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_db),
):
    """Return the full ranking for a stored analysis.

    Recruiters may only access their own analyses.  Admins can access any.
    """
    analysis = (
        await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(404, "Análisis no encontrado.")

    is_admin = current_user.role == UserRole.admin
    if not is_admin and analysis.user_id != current_user.id:
        raise HTTPException(403, "No tenés acceso a este análisis.")

    cat = None
    if analysis.job_category_id:
        cat_row = (
            await db.execute(select(JobCategory).where(JobCategory.id == analysis.job_category_id))
        ).scalar_one_or_none()
        if cat_row:
            cat = {"slug": cat_row.slug, "display_name": cat_row.display_name}

    return {
        "analysis_id": str(analysis.id),
        "ranking": analysis.ranking or [],
        "job_summary": analysis.job_summary,
        "category": cat,
        "anonymized": analysis.anonymized,
    }

