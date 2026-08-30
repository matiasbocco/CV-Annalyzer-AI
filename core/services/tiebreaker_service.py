"""
Tiebreaker service: detect close clusters, generate differentiating questions,
and reorder candidates based on user preferences.

Architecture notes:
- detect_cluster is pure (no I/O) so it can run synchronously before any DB op.
- generate_questions calls the LLM and returns validated Pydantic objects; the
  endpoint serialises them to JSON for storage — we never store raw LLM text.
- apply_answers is also pure: it reweights the four detail dimensions and
  recomputes a score without another LLM call. This is intentional: the answers
  express the *human's* priorities; the *candidates'* scores are fixed facts.
"""

import json
from openai import AsyncOpenAI
from pydantic import ValidationError

from core.config import settings
from core.models.tiebreaker import LLMQuestionsPayload, TiebreakerQuestion

_DIMENSIONS = ("technical_skills", "experience", "education", "soft_skills")

TIEBREAKER_SYSTEM_PROMPT = """\
You are a hiring advisor helping a recruiter choose between candidates with
very similar overall scores.

You will receive a list of candidates in a tiebreaker cluster, including their
detailed dimension scores (0-100 each), strengths, and gaps.

Generate exactly 2 or 3 questions that surface genuine differences between
THESE specific candidates. Each question should ask the hiring manager what
they value more — not generic questions, but ones where the answer would
actually change the ranking given the candidates' profiles.

Each question must have 2–3 options. Each option MUST include weight_adjustments:
a JSON object with exactly these four keys:
  technical_skills, experience, education, soft_skills
Values are integers in [-15, +15]. They represent how much to add to that
dimension's base importance weight (each starts at 25). Use positive numbers to
boost a dimension and negative to reduce it. Adjustments should reflect what
the option implies (e.g. "I care more about hands-on experience" →
experience: +15, education: -10).

Respond in the same language as the job description provided. If the job description is in Spanish, write all questions and options in Spanish.

Reply with valid JSON only:
{
  "questions": [
    {
      "id": "q1",
      "text": "...",
      "options": [
        {
          "id": "a",
          "text": "...",
          "weight_adjustments": {
            "technical_skills": 0,
            "experience": 15,
            "education": -10,
            "soft_skills": 0
          }
        }
      ]
    }
  ]
}
"""


def detect_cluster(ranking: list[dict], threshold: int = 5) -> list[str]:
    """Return filenames of candidates within `threshold` points of the top score.

    Returns an empty list if fewer than 2 candidates qualify — no tiebreaker
    needed when there's a clear winner.
    """
    if len(ranking) < 2:
        return []
    top_score: int = ranking[0]["score"]
    cluster = [c["filename"] for c in ranking if c["score"] >= top_score - threshold]
    return cluster if len(cluster) >= 2 else []


async def generate_questions(
    cluster_data: list[dict],
    llm_client: AsyncOpenAI,
) -> list[TiebreakerQuestion]:
    """Ask the LLM for discriminating questions about the cluster candidates."""
    candidates_summary = json.dumps(
        [
            {
                "filename": c["filename"],
                "score": c["score"],
                "detailed_scores": c["detailed_scores"],
                "strengths": c.get("strengths", []),
                "gaps": c.get("gaps", []),
            }
            for c in cluster_data
        ],
        indent=2,
    )

    response = await llm_client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TIEBREAKER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Tiebreaker cluster:\n{candidates_summary}",
            },
        ],
        max_tokens=1200,
    )

    payload = LLMQuestionsPayload.model_validate_json(
        response.choices[0].message.content
    )
    return payload.questions


def apply_answers(
    cluster_data: list[dict],
    questions: list[dict],
    answers: list[dict],
) -> list[str]:
    """Reorder cluster candidates based on user-supplied answers.

    Strategy:
    1. Start with equal dimension weights [25, 25, 25, 25].
    2. For each answer, look up the selected option's weight_adjustments and
       add the deltas (clamped to ≥0 so no dimension goes negative).
    3. Normalise the resulting weights so they sum to 1.
    4. Recompute a weighted score for each candidate using their existing
       detailed_scores and the new normalised weights.
    5. Sort descending and return filenames.

    This is intentionally *not* another LLM call: the user's answers express
    priorities, the candidates' detailed scores are the ground truth.
    """
    # Build option lookup: (question_id, option_id) → weight_adjustments dict
    option_lookup: dict[tuple[str, str], dict[str, int]] = {}
    for q in questions:
        for opt in q["options"]:
            option_lookup[(q["id"], opt["id"])] = opt.get("weight_adjustments", {})

    weights: dict[str, float] = {d: 25.0 for d in _DIMENSIONS}

    for answer in answers:
        key = (answer["question_id"], answer["option_id"])
        adjustments = option_lookup.get(key, {})
        for dim, delta in adjustments.items():
            if dim in weights:
                weights[dim] = max(0.0, weights[dim] + delta)

    total = sum(weights.values()) or 1.0
    normalised = {k: v / total for k, v in weights.items()}

    def _adjusted_score(candidate: dict) -> float:
        ds = candidate.get("detailed_scores", {})
        return sum(ds.get(dim, 0) * w for dim, w in normalised.items())

    sorted_cluster = sorted(cluster_data, key=_adjusted_score, reverse=True)
    return [c["filename"] for c in sorted_cluster]
