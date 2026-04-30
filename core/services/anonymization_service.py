"""
CV anonymization: strip PII from text and replace filenames with neutral labels
before sending to the LLM, then restore real filenames afterwards.

Why regex instead of LLM for anonymization?
Sending CVs to an LLM to strip PII first, then again to rank them, doubles token
cost and latency. Regex handles the structured formats that appear in CVs (emails,
phone numbers, URLs) precisely and deterministically. The only ambiguous case is
the full name, caught with a conservative first-line heuristic. LLMs are
non-deterministic — a regex miss on an unusual phone format is a minor gap;
a bias introduced because the LLM saw a name or nationality is structural and
invisible in the output.

Why is label_map ephemeral (never stored)?
The map only needs to live for one HTTP request: anonymize → LLM call → restore.
Real filenames are written to analyses.ranking after restoration, so nothing is
lost. Persisting the map would require a dedicated table, foreign keys, and a
cleanup policy for data that can already be reconstructed from the analysis row.

Why does contact info come from MySQL, not from the LLM output?
The LLM never sees real contact data — that is the point. After ranking, real
filenames are restored from label_map; a single DB lookup per filename attaches
the authoritative contact data extracted at ingest time. MySQL is the source of
truth; the LLM output contains no PII at all.

Why store anonymized as a boolean on Analysis?
It creates an audit trail ("was this evaluation potentially biased?") and makes
the field queryable: SELECT COUNT(*) FROM analyses WHERE anonymized = TRUE.
It also allows the API response to be self-documenting so the recruiter UI can
confirm that the model never saw personal data.
"""

import re
import string

# ── Regex patterns ─────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'
)

# Argentine formats: +54 9 11 XXXX-XXXX, (011) XXXX-XXXX, 011-XXXX-XXXX,
# 15-XXXX-XXXX, and generic international / US patterns.
_PHONE_RE = re.compile(
    r'(?:'
    r'\+?54\s*9?\s*\d{2,4}[\s\-\./]\d{3,4}[\s\-\./]\d{3,4}'    # +54 9 11 XXXX-XXXX
    r'|(?:\(0?\d{2,4}\))\s*\d{3,4}[\s\-\.]\d{3,4}'               # (011) XXXX-XXXX
    r'|\b0\d{2,3}\s*[\-\.]?\s*\d{3,4}[\s\-\.]\d{3,4}\b'          # 011 XXXX-XXXX
    r'|\b15[\s\-\.]?\d{4}[\s\-\.]?\d{4}\b'                        # 15-XXXX-XXXX
    r'|\+\d{1,3}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{3,5}[\s\-\.]?\d{3,5}'  # international
    r'|\b\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4}\b'                       # US XXX-XXX-XXXX
    r')'
)

_LINKEDIN_RE = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/in/[^\s,;)\]>\'"]+',
    re.IGNORECASE,
)
_GITHUB_RE = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/[^\s,;)\]>\'"]+',
    re.IGNORECASE,
)
# Any remaining http/https URL (portfolio, personal site, etc.)
_PORTFOLIO_RE = re.compile(r'https?://[^\s,;)\]>\'"]+', re.IGNORECASE)

_AGE_RE = re.compile(
    r'\b\d{1,2}\s*(?:a[ñn]os?|years?\s*old)\b'
    r'|(?:born|nacido(?:/a)?|D\.?O\.?B\.?|fecha\s+de\s+nacimiento)\s*:?\s*\d{4}'
    r'|\b(?:age|edad)\s*:?\s*\d{1,2}\b',
    re.IGNORECASE,
)

# Titles like Sr., Sra., Mr., Ms., Mrs. at a word boundary followed by a space.
_TITLES_RE = re.compile(r'\b(?:Sr|Sra|Mr|Ms|Mrs)\.?\s', re.IGNORECASE)

# A "name line": 2–4 capitalized words (accented chars supported), no digits,
# filling the entire line. Catches "Juan García" and "MARÍA JOSÉ LÓPEZ".
_NAME_LINE_RE = re.compile(
    r'^([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ\-\']+(?:\s+[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ\-\']+){1,3})\s*$'
)


# ── Label generation ──────────────────────────────────────────────────────────

def _label(index: int) -> str:
    """Map index to neutral label: 0→candidate_a, 25→candidate_z, 26→candidate_aa…"""
    letters = string.ascii_lowercase
    if index < 26:
        return f"candidate_{letters[index]}"
    outer = (index // 26) - 1
    inner = index % 26
    return f"candidate_{letters[outer]}{letters[inner]}"


# ── Text scrubbing ────────────────────────────────────────────────────────────

def _scrub(text: str) -> str:
    """Replace PII in a single CV's text with neutral placeholders.

    Order is intentional: specific URL patterns before the generic portfolio
    catch-all, and URLs before emails (no interference between them in practice,
    but keeps the logic explicit).
    """
    text = _LINKEDIN_RE.sub('[linkedin]', text)
    text = _GITHUB_RE.sub('[github]', text)
    text = _PORTFOLIO_RE.sub('[portfolio]', text)
    text = _EMAIL_RE.sub('[email]', text)
    text = _PHONE_RE.sub('[phone]', text)
    text = _AGE_RE.sub('[age]', text)
    text = _TITLES_RE.sub('', text)

    # Replace name-looking lines in the first 3 non-empty lines.
    lines = text.split('\n')
    checked = 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if checked >= 3:
            break
        if _NAME_LINE_RE.match(line.strip()):
            lines[i] = '[name]'
        checked += 1

    return '\n'.join(lines)


# ── Public API ────────────────────────────────────────────────────────────────

def anonymize_cvs(
    cvs: list[dict],
) -> tuple[list[dict], dict[str, str]]:
    """Replace real filenames with neutral labels and strip PII from text.

    Args:
        cvs: list of dicts, each with at least {"filename": str, "text": str}.
             Extra keys (source, cv_id, …) are preserved unchanged.

    Returns:
        anonymized_cvs: same structure; filename and text replaced, rest intact.
        label_map:      {"candidate_a": "real_filename.pdf", …}
    """
    label_map: dict[str, str] = {}
    anonymized: list[dict] = []

    for i, cv in enumerate(cvs):
        label = _label(i)
        label_map[label] = cv["filename"]
        anonymized.append({**cv, "filename": label, "text": _scrub(cv["text"])})

    return anonymized, label_map


def restore_filenames(
    ranking: list[dict],
    label_map: dict[str, str],
) -> list[dict]:
    """Swap anonymized labels back to real filenames in an LLM ranking.

    Labels not found in label_map are passed through unchanged (defensive
    against an LLM that invents a filename not in the input).
    """
    return [
        {**entry, "filename": label_map.get(entry["filename"], entry["filename"])}
        for entry in ranking
    ]
