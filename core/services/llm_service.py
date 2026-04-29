"""
LLM service: ranking and OpenAI client singleton.

Why are bank CVs passed as full candidates (not as calibration references)?

If bank CVs were injected only as "background context" and not ranked, the
model's evaluation of the uploaded CVs would still be influenced by the bank
content but we'd have no structured score for those bank candidates.  Passing
them as full candidates:
  a) Gives each bank CV a score on the same 0-100 scale as uploaded CVs,
     making the recency-factor multiplication directly comparable.
  b) Lets the recruiter see bank candidates ranked against live uploads in one
     unified list, which is the product value proposition.
  c) Avoids a separate "bank-only" scoring call that would double the LLM cost.

The unified ranking approach requires that bank CVs be clearly labelled in the
prompt (separate XML block) so the model knows their provenance without
confusing uploaded vs bank content.
"""

from openai import AsyncOpenAI

from core.config import settings
from core.models.response import RankingResponse

client = AsyncOpenAI(api_key=settings.openai_api_key)

RANKING_SYSTEM_PROMPT = (
    "You are an expert HR recruiter. You will receive a job description and "
    "MULTIPLE candidate CVs. Evaluate EVERY candidate (whether uploaded or "
    "from the bank) against the job description using the same criteria and "
    "the same scoring weights.\n\n"
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
    job_description: str,
    uploaded_cvs: list[tuple[str, str]],
    bank_cvs: list[dict] | None = None,
) -> str:
    """Build the user message.

    When bank_cvs are present, CVs are split into labelled XML blocks so the
    model can identify their origin.  When there are no bank_cvs, the original
    flat format is used for backward compatibility.
    """
    if bank_cvs:
        uploaded_block = "\n\n".join(
            f'<cv filename="{fn}">\n{text}\n</cv>' for fn, text in uploaded_cvs
        )
        bank_block = "\n\n".join(
            f'<cv filename="{d["filename"]}">\n{d["text"]}\n</cv>' for d in bank_cvs
        )
        parts = [f"JOB DESCRIPTION:\n{job_description}"]
        if uploaded_cvs:
            parts.append(f"UPLOADED CANDIDATE CVS:\n<uploaded_cvs>\n{uploaded_block}\n</uploaded_cvs>")
        if bank_cvs:
            parts.append(f"BANK CANDIDATE CVS (past analyses — evaluate as equals):\n<bank_cvs>\n{bank_block}\n</bank_cvs>")
        return "\n\n".join(parts)

    # Original flat format — only uploaded CVs.
    cv_blocks = "\n\n".join(
        f'<cv filename="{fn}">\n{text}\n</cv>' for fn, text in uploaded_cvs
    )
    return f"JOB DESCRIPTION:\n{job_description}\n\nCANDIDATE CVS:\n{cv_blocks}"


async def rank_candidates(
    job_description: str,
    uploaded_cvs: list[tuple[str, str]],
    bank_cvs: list[dict] | None = None,
) -> RankingResponse:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RANKING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_content(job_description, uploaded_cvs, bank_cvs),
            },
        ],
    )
    return RankingResponse.model_validate_json(response.choices[0].message.content)
