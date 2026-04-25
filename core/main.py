from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import ValidationError

from core.services.llm_service import rank_candidates, test_connection
from core.services.pdf_service import extract_text

app = FastAPI(title="CV Analyzer AI")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/test", include_in_schema=False)
def test_ui():
    return FileResponse(STATIC_DIR / "test.html")


@app.get("/test-llm")
async def test_llm():
    result = await test_connection()
    return {"response": result}


@app.post("/analyze")
async def analyze(
    files: Annotated[
        list[UploadFile],
        File(description="One or more candidate CVs in PDF format"),
    ],
    job_description: Annotated[
        str,
        Form(description="Job description to evaluate the candidates against"),
    ],
):
    cvs: list[tuple[str, str]] = []

    for file in files:
        file_bytes = await file.read()

        try:
            cv_text = extract_text(file_bytes)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or unreadable PDF: {file.filename}",
            )

        if not cv_text.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"PDF contains no extractable text "
                    f"(is it a scanned image?): {file.filename}"
                ),
            )

        cvs.append((file.filename, cv_text))

    try:
        return await rank_candidates(job_description, cvs)
    except ValidationError as e:
        raise HTTPException(
            status_code=502,
            detail={"message": "LLM returned malformed data", "errors": e.errors()},
        )
    except OpenAIError as e:
        raise HTTPException(status_code=503, detail=f"OpenAI unavailable: {e}")
