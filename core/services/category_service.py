"""
LLM-based job category classifier.

Why LLM classification instead of rule-based (keyword matching)?
Job descriptions are free-form text: "we need a Pythonista who loves k8s" is
semantically backend-developer-python but shares no keyword with its slug.
LLMs handle this without a handcrafted keyword list.

The function is intentionally tolerant: any failure (LLM error, bad JSON,
unknown slug) returns None rather than raising, so the /analyze endpoint
can degrade gracefully without blocking the main ranking result.
"""

import json
from typing import Literal, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db.models import JobCategory

CATEGORY_SYSTEM_PROMPT = """\
You are a job-role classifier for an AI recruitment tool.

Given a job description and a list of existing categories, decide whether it
belongs to one of the existing categories or requires a new one.

Rules:
- Prefer matching an existing category — only create a new one when the role is
  in a domain clearly not covered.
- A new slug must be lowercase and hyphen-separated (e.g. "blockchain-developer").
- required_skills must be a list of 5-10 key skills.

Respond with valid JSON only, no commentary:
  {"action": "match", "slug": "<existing-slug>", "new_category": null}
OR
  {"action": "create", "slug": "<new-slug>", "new_category": {
     "slug": "...", "display_name": "...",
     "description": "...", "required_skills": [...]}}
"""


class _NewCategory(BaseModel):
    slug: str
    display_name: str
    description: str
    required_skills: list[str]


class _Classification(BaseModel):
    action: Literal["match", "create"]
    slug: str
    new_category: Optional[_NewCategory] = None


async def get_or_create_category(
    db: AsyncSession,
    job_description: str,
    llm_client: AsyncOpenAI,
) -> Optional[JobCategory]:
    """Classify job_description → existing or new JobCategory.

    Returns None on any failure so callers can degrade gracefully.
    """
    result = await db.execute(select(JobCategory))
    categories: list[JobCategory] = list(result.scalars().all())

    if not categories:
        return None

    categories_summary = json.dumps(
        [
            {
                "slug": c.slug,
                "display_name": c.display_name,
                "description": c.description[:200],
            }
            for c in categories
        ],
        indent=2,
    )
    user_content = (
        f"Available categories:\n{categories_summary}\n\n"
        f"Job description:\n{job_description[:2500]}"
    )

    try:
        response = await llm_client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CATEGORY_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=600,
        )
        classification = _Classification.model_validate_json(
            response.choices[0].message.content
        )
    except (ValidationError, Exception):
        return None

    if classification.action == "match":
        return next((c for c in categories if c.slug == classification.slug), None)

    if classification.action == "create" and classification.new_category:
        nd = classification.new_category
        # Guard against duplicate slug from a race or repeated LLM mistake.
        existing = next((c for c in categories if c.slug == nd.slug), None)
        if existing:
            return existing

        new_cat = JobCategory(
            slug=nd.slug,
            display_name=nd.display_name,
            description=nd.description,
            required_skills=nd.required_skills,
        )
        db.add(new_cat)
        # Flush so the PK is available before the Analysis row referencing it
        # is added to the same session and committed in one transaction.
        await db.flush()
        return new_cat

    return None
