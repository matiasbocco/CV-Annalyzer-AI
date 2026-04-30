import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
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
from core.services.category_service import get_or_create_category
from core.services.contact_service import extract_contact_info
from core.services.cv_bank_service import ingest_cv, update_bank_cv_seen
from core.services.embedding_service import compute_text_hash, generate_embedding
from core.services.llm_service import client as llm_client
from core.services.llm_service import rank_candidates, test_connection
from core.services.pdf_service import extract_text
from core.services.recency_service import compute_recency_factor, nivel_from_score
from core.services.tiebreaker_service import (
    apply_answers,
    detect_cluster,
    generate_questions,
)
from core.services.ttl_service import expire_old_cvs

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
        await _check_bank_drift(db)
    yield

app = FastAPI(title="CV Analyzer AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


class MatchJobRequest(BaseModel):
    job_description: str
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
async def list_categories(db: AsyncSession = Depends(get_db)):
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

@app.post("/analyze", status_code=201)
async def analyze(
    files: Annotated[list[UploadFile], File(description="One or more CV PDFs")],
    job_description: Annotated[str, Form(description="Job description text")],
    include_bank: Annotated[bool, Form(description="Merge top bank candidates into ranking")] = False,
    db: AsyncSession = Depends(get_db),
):
    # 1. Extract uploaded PDFs.
    cvs: list[tuple[str, str]] = []
    for file in files:
        raw = await file.read()
        try:
            text = extract_text(raw)
        except Exception:
            raise HTTPException(400, f"Invalid PDF: {file.filename}")
        if not text.strip():
            raise HTTPException(422, f"No extractable text: {file.filename}")
        cvs.append((file.filename, text))

    uploaded_hashes = {compute_text_hash(text) for _, text in cvs}

    # 2. Semantic search for bank candidates — only when explicitly requested.
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

    # 3. LLM ranking.
    try:
        result = await rank_candidates(job_description, cvs, bank_cvs=bank_cvs_for_llm or None)
    except ValidationError as e:
        raise HTTPException(502, {"message": "LLM returned malformed data", "errors": e.errors()})
    except OpenAIError as e:
        raise HTTPException(503, f"OpenAI unavailable: {e}")

    # 4. Enrich ranking with source and recency factor; re-sort by adjusted score.
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

    # 5. Classify job description (tolerant).
    category = await get_or_create_category(db, job_description, llm_client)

    # 6. Persist Analysis row.
    analysis = Analysis(
        job_description=job_description,
        ranking=[c.model_dump() for c in enriched],
        job_summary=result.job_summary,
        model_used=settings.openai_model,
        job_category_id=category.id if category else None,
    )
    db.add(analysis)
    await db.commit()

    # 7. Ingest uploaded CVs into the bank (after commit — see module docstring).
    filename_to_cv: dict[str, CV] = {}
    try:
        for filename, text in cvs:
            cv, _ = await ingest_cv(db, filename, text)
            filename_to_cv[filename] = cv
        await db.commit()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("CV bank ingestion failed: %s", exc)

    # 8. Update bank CVs that were pulled into this analysis.
    try:
        for bank_cv in bank_cv_records:
            filename_to_cv[bank_cv.filename] = bank_cv
            await update_bank_cv_seen(db, bank_cv)
        await db.commit()
    except Exception:
        pass

    # 9. Create per-candidate CVAnalysis rows (best-effort).
    try:
        await _persist_cv_analyses(db, analysis.id, enriched, filename_to_cv)
    except Exception:
        pass

    # 10. Attach contact info from CV rows to ranking entries.
    for candidate in enriched:
        candidate.contact = _build_contact(filename_to_cv.get(candidate.filename))

    return AnalyzeResponse(
        analysis_id=analysis.id,
        ranking=enriched,
        job_summary=result.job_summary,
        category=CategoryInfo(slug=category.slug, display_name=category.display_name)
        if category else None,
    )


# ── Candidate upload — Step 1: extract contact info (no DB write) ─────────────

CRITICAL_CONTACT_FIELDS = {"full_name", "email", "availability"}

@app.post("/cvs/extract-contact")
async def extract_cv_contact(
    file: Annotated[UploadFile, File(description="PDF to extract contact info from")],
):
    """Extract contact info from a PDF without saving anything.

    Returns the extracted fields plus a list of critical missing fields so
    the UI can prompt the candidate to fill them before final upload.
    """
    fname = file.filename or "cv.pdf"
    try:
        raw = await file.read()
        text = extract_text(raw)
    except Exception:
        raise HTTPException(400, "El archivo no es un PDF válido.")

    if not text.strip():
        raise HTTPException(422, "No se pudo extraer texto. ¿Es un PDF escaneado?")

    text_hash = compute_text_hash(text)
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
    file: Annotated[UploadFile, File(description="Candidate's CV in PDF format")],
    contact_info: Annotated[str, Form(description="JSON contact fields")] = "{}",
    expected_hash: Annotated[str, Form(description="Hash from extract-contact step")] = "",
    db: AsyncSession = Depends(get_db),
):
    import json as _json

    fname = file.filename or "cv.pdf"
    try:
        raw  = await file.read()
        text = extract_text(raw)
    except Exception:
        return JSONResponse(status_code=400, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": "El archivo no es un PDF válido.",
        })

    if not text.strip():
        return JSONResponse(status_code=400, content={
            "status": "failed", "filename": fname, "cv_id": None,
            "message": "No se pudo extraer texto del PDF.",
        })

    # Hash verification — ensures the uploaded file matches the extraction step.
    actual_hash = compute_text_hash(text)
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
        import logging
        logging.getLogger(__name__).error("CV ingest failed: %s", exc)
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

@app.post("/match-job", status_code=201)
async def match_job(
    body: MatchJobRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rank bank CVs against a job description without uploading new files."""
    try:
        job_embedding = await generate_embedding(body.job_description)
    except Exception as e:
        raise HTTPException(502, f"Embedding generation failed: {e}")

    bank_cv_records = await _search_bank(job_embedding, set(), body.top_n, db)
    if not bank_cv_records:
        raise HTTPException(404, "No suitable candidates found in the bank.")

    bank_cvs_for_llm = [
        {"filename": cv.filename, "text": cv.text_content}
        for cv in bank_cv_records
    ]

    try:
        result = await rank_candidates(
            body.job_description,
            uploaded_cvs=[],
            bank_cvs=bank_cvs_for_llm,
        )
    except ValidationError as e:
        raise HTTPException(502, {"message": "LLM returned malformed data", "errors": e.errors()})
    except OpenAIError as e:
        raise HTTPException(503, f"OpenAI unavailable: {e}")

    bank_cv_by_filename = {cv.filename: cv for cv in bank_cv_records}

    enriched: list[CandidateRankingWithSource] = []
    for candidate in result.ranking:
        bank_cv = bank_cv_by_filename.get(candidate.filename)
        factor = compute_recency_factor(bank_cv.created_at) if bank_cv else 1.0
        c = _enrich_candidate(candidate, "bank", factor)
        c.contact = _build_contact(bank_cv)
        enriched.append(c)

    enriched.sort(key=lambda c: c.score, reverse=True)

    category = await get_or_create_category(db, body.job_description, llm_client)

    analysis = Analysis(
        job_description=body.job_description,
        ranking=[c.model_dump() for c in enriched],
        job_summary=result.job_summary,
        model_used=settings.openai_model,
        job_category_id=category.id if category else None,
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
    )


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.post("/analyses/{analysis_id}/feedback")
async def submit_feedback(
    analysis_id: uuid.UUID,
    body: FeedbackRequest,
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


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.post("/admin/expire-cvs")
async def admin_expire_cvs(db: AsyncSession = Depends(get_db)):
    count = await expire_old_cvs(db)
    return {"expired": count}
