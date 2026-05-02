"""
Tests for input validation rules:
  - File size limit (5 MB)          — service level
  - PDF page limit (3 pages)        — service level
  - Max 10 files per /analyze       — endpoint level
  - Job description max 3000 chars  — endpoint level
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_db_override():
    """FastAPI dependency override that yields a no-op mock session."""
    async def _mock_db():
        yield MagicMock()
    return _mock_db


# ── File size limit ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_file_over_5mb_raises_400():
    from core.services.file_extraction_service import extract_text_from_bytes
    big = b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc_info:
        await extract_text_from_bytes(big, "big.pdf")
    assert exc_info.value.status_code == 400
    assert "5 MB" in exc_info.value.detail


# ── PDF page limit ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_pdf_over_3_pages_raises_400():
    from core.services.file_extraction_service import extract_text_from_bytes

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Content"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = lambda s: s
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_ctx.pages = [mock_page] * 4  # 4 pages — exceeds limit

    with patch("core.services.file_extraction_service.pdfplumber.open", return_value=mock_ctx):
        with pytest.raises(HTTPException) as exc_info:
            await extract_text_from_bytes(b"%PDF-1.4", "long_cv.pdf")

    assert exc_info.value.status_code == 400
    assert "páginas" in exc_info.value.detail
    assert "4" in exc_info.value.detail  # reports actual page count


@pytest.mark.anyio
async def test_pdf_3_pages_is_accepted():
    from core.services.file_extraction_service import extract_text_from_bytes

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "CV content here"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = lambda s: s
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_ctx.pages = [mock_page] * 3  # exactly 3 pages — should pass

    with patch("core.services.file_extraction_service.pdfplumber.open", return_value=mock_ctx):
        text = await extract_text_from_bytes(b"%PDF-1.4", "cv.pdf")

    assert "CV content" in text


# ── /analyze: max 10 files ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_too_many_files_returns_400():
    from httpx import ASGITransport, AsyncClient
    from core.main import app
    from core.db.database import get_db

    app.dependency_overrides[get_db] = _make_db_override()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = [
                ("files", (f"cv{i}.pdf", b"%PDF-1.4", "application/pdf"))
                for i in range(11)
            ]
            resp = await client.post(
                "/analyze",
                files=files,
                data={"job_description": "a" * 60, "include_bank": "false"},
            )
        assert resp.status_code == 400
        assert "10" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── /analyze: job description too long ───────────────────────────────────────

@pytest.mark.anyio
async def test_job_description_too_long_returns_422():
    from httpx import ASGITransport, AsyncClient
    from core.main import app
    from core.db.database import get_db

    app.dependency_overrides[get_db] = _make_db_override()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = [("files", ("cv.pdf", b"%PDF-1.4", "application/pdf"))]
            resp = await client.post(
                "/analyze",
                files=files,
                data={"job_description": "a" * 3001, "include_bank": "false"},
            )
        assert resp.status_code == 422
        assert "3000" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
