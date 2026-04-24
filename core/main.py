from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from openai import OpenAIError
from pydantic import ValidationError

from core.services.llm_service import analyze_cv, test_connection
from core.services.pdf_service import extract_text

app = FastAPI(title="CV Analyzer AI")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/test-llm")
async def test_llm():
    result = await test_connection()
    return {"response": result}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    file_bytes = await file.read()

    try:
        cv_text = extract_text(file_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or unreadable PDF")

    if not cv_text.strip():
        raise HTTPException(
            status_code=422,
            detail="PDF contains no extractable text (is it a scanned image?)",
        )

    try:
        return await analyze_cv(cv_text, job_description)
    except ValidationError as e:
        raise HTTPException(
            status_code=502,
            detail={"message": "LLM returned malformed data", "errors": e.errors()},
        )
    except OpenAIError as e:
        raise HTTPException(status_code=503, detail=f"OpenAI unavailable: {e}")
