"""LLM-based contact information extraction from CV text.

Design notes:
- Uses gpt-4o-mini with json_object response_format — fast and cheap for
  structured extraction, no parsing heuristics needed.
- Text is truncated to 6 000 chars: contact info is always at the top/bottom
  of a CV; feeding the full document wastes tokens for no gain.
- All fields are nullable. The LLM is explicitly instructed NOT to infer.
- HttpUrl fields are serialised to plain strings before returning so callers
  can write them directly to VARCHAR columns without extra conversion.
- The whole function is wrapped in a broad try/except so a failure here
  never breaks the ingest flow — we just skip contact extraction and log.
"""

import json
import logging
from typing import Optional

from pydantic import ValidationError

from core.models.response import ContactExtraction
from core.services.llm_service import client as _openai_client

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a contact-information extractor for CVs/resumes.
Your job is to return a JSON object with these exact keys:

  full_name, email, phone, linkedin_url, github_url, portfolio_url, location, availability

Rules:
1. Extract ONLY what is literally present in the text. Do NOT infer, guess, or generate.
2. Return null for any field not found.
3. email: must be a valid email address format.
4. linkedin_url: only if the URL contains "linkedin.com". Otherwise null.
5. github_url: only if the URL contains "github.com". Otherwise null.
6. portfolio_url: any other personal URL (personal site, Behance, Kaggle, etc.).
   If a URL contains neither "linkedin.com" nor "github.com", put it here.
7. location: city, province/state, or country as written. One string.
8. availability: ONLY set if the CV explicitly states job search status.
   - "available"  → actively looking, immediately available, open to new roles
   - "open"       → open to opportunities but not urgently searching
   - "not_looking"→ not currently looking / not open to offers
   - null         → not mentioned at all (most common case)
9. Respond ONLY with the JSON object. No explanation, no markdown.
"""


_URL_FIELDS = ("linkedin_url", "github_url", "portfolio_url")


def _normalize_urls(raw: dict) -> None:
    """Prepend https:// to URL fields that the LLM returned without a scheme."""
    for field in _URL_FIELDS:
        v = raw.get(field)
        if isinstance(v, str) and v and "://" not in v:
            raw[field] = "https://" + v


def _url_to_str(value) -> Optional[str]:
    """Convert a Pydantic HttpUrl (or None) to a plain string."""
    if value is None:
        return None
    s = str(value)
    # Pydantic v2 HttpUrl.str() always has a trailing slash for bare domains;
    # strip it only when the path is just "/" to keep real paths intact.
    if s.endswith("/") and s.count("/") == 3:
        s = s.rstrip("/")
    return s


async def extract_contact_info(cv_text: str) -> dict:
    """Return a dict of contact fields extracted from cv_text.

    Keys match the CV model columns:
      full_name, email, phone, linkedin_url, github_url,
      portfolio_url, location, availability

    All values are str | None (never HttpUrl objects).
    Returns an empty dict on any failure so callers can skip gracefully.
    """
    # Contact info lives near the top; cap at 6 000 chars to save tokens.
    excerpt = cv_text[:6_000]

    try:
        response = await _openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": excerpt},
            ],
        )
        raw: dict = json.loads(response.choices[0].message.content)
    except Exception as exc:
        log.warning("extract_contact_info LLM call failed: %s", exc)
        return {}

    _normalize_urls(raw)

    try:
        parsed = ContactExtraction.model_validate(raw)
    except ValidationError as exc:
        log.warning("ContactExtraction validation failed: %s", exc)
        return {}

    return {
        "full_name":      parsed.full_name,
        "email":          str(parsed.email) if parsed.email else None,
        "phone":          parsed.phone,
        "linkedin_url":   _url_to_str(parsed.linkedin_url),
        "github_url":     _url_to_str(parsed.github_url),
        "portfolio_url":  _url_to_str(parsed.portfolio_url),
        "location":       parsed.location,
        "availability":   parsed.availability,
    }
