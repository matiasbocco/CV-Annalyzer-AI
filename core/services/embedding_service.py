"""
Text hashing and embedding generation.

compute_text_hash uses SHA-256 of the *normalised* text so that trivial
formatting differences (extra spaces, case) between two identical CVs don't
create duplicate rows.  The normalisation must be applied consistently
everywhere the hash is computed — both at ingestion and at dedup checks.
"""

import hashlib
import re

from core.services.llm_service import client as _openai_client

_EMBEDDING_MODEL = "text-embedding-3-small"


def normalize_text(text: str) -> str:
    """Strip, lowercase, collapse all whitespace to single spaces."""
    return re.sub(r"\s+", " ", text.strip().lower())


def compute_text_hash(text: str) -> str:
    """SHA-256 of normalised text.  Returns a 64-character hex string."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


async def generate_embedding(text: str) -> list[float]:
    """Return a 1 536-dimension embedding vector for the given text."""
    response = await _openai_client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=normalize_text(text),
    )
    return response.data[0].embedding
