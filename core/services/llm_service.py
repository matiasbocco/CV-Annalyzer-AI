import json
from openai import AsyncOpenAI
from core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

ANALYZE_SYSTEM_PROMPT = (
    "You are an expert HR recruiter. Analyze the compatibility between the "
    "candidate and the job.\n\n"
    "Evaluate the candidate across four independent dimensions BEFORE giving "
    "the overall score. For each dimension, assign a 0-100 value:\n"
    "1. technical_skills: hard skills, tools, languages, frameworks, and "
    "technical certifications required by the job.\n"
    "2. experience: years, seniority, relevance of past roles, industry fit, "
    "and scope of responsibilities vs. what the job demands.\n"
    "3. education: formal degrees, relevant coursework, and certifications "
    "aligned with the role.\n"
    "4. soft_skills: communication, leadership, teamwork, adaptability, and "
    "any behavioral traits mentioned in the job description.\n\n"
    "The overall 'score' must be a weighted synthesis of the four dimensions "
    "(do NOT just average them — weight by how critical each is for this "
    "specific job). Derive 'nivel' from 'score': 0-40 bajo, 41-65 medio, "
    "66-85 alto, 86-100 excelente.\n\n"
    "Reply ONLY with valid JSON matching this exact shape:\n"
    "{\n"
    '  "score": int 0-100,\n'
    '  "nivel": "bajo"|"medio"|"alto"|"excelente",\n'
    '  "detailed_scores": {\n'
    '    "technical_skills": int 0-100,\n'
    '    "experience": int 0-100,\n'
    '    "education": int 0-100,\n'
    '    "soft_skills": int 0-100\n'
    "  },\n"
    '  "strengths": string[] (max 5),\n'
    '  "gaps": string[] (max 4),\n'
    '  "recommendations": string[] (max 3),\n'
    '  "summary": string\n'
    "}"
)


async def test_connection() -> str:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
    )
    return response.choices[0].message.content


async def analyze_cv(cv_text: str, job_description: str) -> dict:
    user_content = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"CANDIDATE CV:\n{cv_text}"
    )
    response = await client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return json.loads(response.choices[0].message.content)
