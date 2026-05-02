"""
Multi-format CV text extraction.

Supported formats:
  .pdf   — pdfplumber (existing logic, moved here from pdf_service.py)
  .docx  — python-docx (paragraphs + table cells)
  .jpg / .jpeg / .png / .webp — OpenAI Vision API (gpt-4o-mini)

Public interface:
  extract_text_from_bytes(raw, filename) -> str   # primary; used by endpoints
  extract_text(file: UploadFile) -> str           # thin wrapper; reads then delegates
"""

import base64
import io
import re
from pathlib import Path

import pdfplumber
from fastapi import HTTPException, UploadFile
from openai import OpenAIError

from core.services.llm_service import client as _llm_client

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".webp"}

_IMAGE_MIME: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
}

_VISION_SYSTEM_PROMPT = (
    "You are a CV parser. Extract all text content from this CV image exactly as it "
    "appears. Return only the extracted text, no commentary."
)

_MAX_WORDS = 12_000
_TRUNCATION_SUFFIX = " [... CV truncated]"


# ── Shared post-processing ────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Collapse excess whitespace and truncate to _MAX_WORDS."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    words = text.split()
    if len(words) > _MAX_WORDS:
        return " ".join(words[:_MAX_WORDS]) + _TRUNCATION_SUFFIX
    return text


# ── Format-specific extractors ────────────────────────────────────────────────

def _extract_pdf(raw: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        pages = [page.extract_text(layout=True) or "" for page in pdf.pages]
    return _clean("\n".join(pages))


def _extract_docx(raw: bytes) -> str:
    """Extract text from DOCX bytes using python-docx.

    Includes both paragraph text and table cell text because many CVs use
    tables for layout (skills matrix, education table, etc.).
    """
    import docx  # lazy import — only needed for DOCX files

    doc = docx.Document(io.BytesIO(raw))
    parts: list[str] = []

    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)

    return _clean("\n".join(parts))


async def _extract_image(raw: bytes, ext: str) -> str:
    """Extract CV text from an image using OpenAI Vision (gpt-4o-mini).

    Encodes the image as a base64 data URL and asks the model to return
    the raw text content of the CV. Uses 'high' detail for better OCR
    accuracy on dense CV layouts.
    """
    mime = _IMAGE_MIME[ext]
    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('utf-8')}"

    try:
        response = await _llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"},
                        }
                    ],
                },
            ],
            max_tokens=4096,
        )
    except OpenAIError as exc:
        raise HTTPException(502, f"Vision API unavailable: {exc}") from exc

    text = response.choices[0].message.content or ""
    return _clean(text)


# ── Public API ────────────────────────────────────────────────────────────────

async def extract_text_from_bytes(raw: bytes, filename: str) -> str:
    """Detect file type from extension and extract CV text.

    Raises HTTPException 400 for unsupported extensions or corrupt files.
    This is the primary function used by endpoint code that has already
    read raw bytes (e.g. to compute a hash before extraction).
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        accepted = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Accepted formats: {accepted}",
        )

    try:
        if ext == ".pdf":
            return _extract_pdf(raw)
        if ext == ".docx":
            return _extract_docx(raw)
        return await _extract_image(raw, ext)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not extract text from '{filename}': {exc}") from exc


async def extract_text(file: UploadFile) -> str:
    """Thin wrapper: read UploadFile bytes then delegate to extract_text_from_bytes."""
    raw = await file.read()
    return await extract_text_from_bytes(raw, file.filename or "")
