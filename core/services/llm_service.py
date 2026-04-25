from openai import AsyncOpenAI

from core.config import settings
from core.models.response import RankingResponse

client = AsyncOpenAI(api_key=settings.openai_api_key)

RANKING_SYSTEM_PROMPT = (
    "You are an expert HR recruiter. You will receive a job description and "
    "MULTIPLE candidate CVs, each labeled with its filename. Analyze every "
    "candidate against the job and rank them.\n\n"
    "For EACH candidate, evaluate four independent dimensions BEFORE giving "
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
    "specific job). Apply the SAME weighting scheme to every candidate so "
    "they are directly comparable. Derive 'nivel' from 'score': 0-40 bajo, "
    "41-65 medio, 66-84 alto, 85-100 excelente.\n\n"
    "Sort 'ranking' from highest 'score' to lowest. Also produce 'job_summary': "
    "2-3 sentences describing the ideal candidate profile based on the job "
    "description (independent of the CVs received).\n\n"
    "Reply ONLY with valid JSON matching this exact shape:\n"
    "{\n"
    '  "ranking": [\n'
    "    {\n"
    '      "filename": string,\n'
    '      "score": int 0-100,\n'
    '      "nivel": "bajo"|"medio"|"alto"|"excelente",\n'
    '      "detailed_scores": {\n'
    '        "technical_skills": int 0-100,\n'
    '        "experience": int 0-100,\n'
    '        "education": int 0-100,\n'
    '        "soft_skills": int 0-100\n'
    "      },\n"
    '      "strengths": string[] (max 3),\n'
    '      "gaps": string[] (max 3),\n'
    '      "recommendations": string[] (max 2),\n'
    '      "summary": string (2-3 sentences)\n'
    "    }\n"
    "  ],\n"
    '  "job_summary": string\n'
    "}"
)


async def test_connection() -> str:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
    )
    return response.choices[0].message.content


def _build_user_content(
    job_description: str, cvs: list[tuple[str, str]]
) -> str:
    cv_blocks = "\n\n".join(
        f'<cv filename="{filename}">\n{text}\n</cv>'
        for filename, text in cvs
    )
    return (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"CANDIDATE CVS:\n{cv_blocks}"
    )


async def rank_candidates(
    job_description: str, cvs: list[tuple[str, str]]
) -> RankingResponse:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RANKING_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(job_description, cvs)},
        ],
    )
    return RankingResponse.model_validate_json(
        response.choices[0].message.content
    )
