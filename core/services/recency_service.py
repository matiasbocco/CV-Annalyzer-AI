"""
Recency factor computation.

Why is the recency factor applied to scores AFTER the LLM ranking, not inside
the prompt?

1. Determinism: injecting time-decay instructions into a prompt makes the
   model's weighting of recency unpredictable and un-testable.  Applying a
   numeric multiplier in Python is deterministic and trivially auditable.

2. Separation of concerns: the LLM evaluates skill fit; time-decay is a
   business rule about data freshness.  These are orthogonal concerns; mixing
   them in a prompt risks the model conflating recency with quality.

3. Auditability: the recency_factor_applied column in cv_analyses records the
   exact multiplier used.  If we changed the decay schedule, historical rows
   are unaffected and comparable.  A prompt-based approach would silently
   change past results if we retried the LLM call.
"""

from datetime import datetime, timezone


def compute_recency_factor(last_seen_at: datetime) -> float:
    """Return a multiplier in {1.0, 0.7, 0.0} based on CV freshness.

    Uses last_seen_at, not created_at.  A CV created 2 years ago but
    re-uploaded last week is fresh; created_at would wrongly penalise it.
    last_seen_at is updated every time the CV is uploaded or pulled into a
    match, so it reflects actual recruiter activity — the right signal for
    whether the candidate is still being considered.

    - 0–3 months since last seen  → 1.0  (full score)
    - 3–4 months since last seen  → 0.7  (moderate penalty — still usable)
    - >4 months since last seen   → 0.0  (defensive zero; should already be expired)
    """
    now = datetime.now(timezone.utc)
    # Make last_seen_at timezone-aware if it isn't (MySQL returns naive UTC).
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)

    age_days = (now - last_seen_at).days

    if age_days <= 90:    # 0–3 months
        return 1.0
    elif age_days <= 120: # 3–4 months
        return 0.7
    else:                 # >4 months (expired territory)
        return 0.0


def nivel_from_score(score: int) -> str:
    """Derive nivel label from a 0-100 score (mirrors CandidateRanking validator)."""
    if score <= 40:
        return "bajo"
    elif score <= 65:
        return "medio"
    elif score <= 84:
        return "alto"
    else:
        return "excelente"
