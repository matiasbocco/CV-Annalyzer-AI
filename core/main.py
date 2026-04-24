from fastapi import FastAPI
from core.services.llm_service import test_connection

app = FastAPI(title="CV Analyzer AI")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/test-llm")
async def test_llm():
    result = await test_connection()
    return {"response": result}
