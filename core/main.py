from fastapi import FastAPI, File, Form, UploadFile
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
    cv_text = extract_text(file_bytes)
    return await analyze_cv(cv_text, job_description)
