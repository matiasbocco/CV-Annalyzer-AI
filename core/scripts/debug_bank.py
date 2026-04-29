"""Inspect the CV bank state in PostgreSQL and ChromaDB.

Usage:
    python -m core.scripts.debug_bank
"""

import asyncio
import sys

# Force UTF-8 output on Windows so box-drawing chars don't crash cp1252.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import func, select

from core.db.database import AsyncSessionLocal
from core.db.models import CV
from core.services import vector_service
from core.services.embedding_service import generate_embedding

DIV  = "-" * 72
DIV2 = "=" * 72
SAMPLE_QUERY = "Senior Python Backend Developer FastAPI"


def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)


async def section_postgres() -> None:
    print(f"\n{DIV2}")
    print("  1 · PostgreSQL  —  cvs table")
    print(DIV2)

    async with AsyncSessionLocal() as db:
        total: int = (
            await db.execute(select(func.count()).select_from(CV))
        ).scalar_one()

        print(f"\n  Total rows: {total}\n")

        if total == 0:
            print("  (bank is empty — upload CVs via /cvs/batch or run /analyze)\n")
            return

        rows = (
            await db.execute(select(CV).order_by(CV.created_at))
        ).scalars().all()

        # Header
        cols = (
            f"  {'#':>3}  "
            f"{'ID':36}  "
            f"{'Filename':<34}  "
            f"{'Hash[:16]':16}  "
            f"{'Created':16}  "
            f"{'Last seen':16}  "
            f"{'Exp':3}  "
            f"Emb"
        )
        print(cols)
        print(f"  {DIV}")

        for i, cv in enumerate(rows, 1):
            filename = cv.filename
            if len(filename) > 34:
                filename = filename[:31] + "…"
            print(
                f"  {i:>3}  "
                f"{str(cv.id):36}  "
                f"{filename:<34}  "
                f"{cv.text_hash[:16]:16}  "
                f"{_fmt_dt(cv.created_at):16}  "
                f"{_fmt_dt(cv.last_seen_at):16}  "
                f"{'YES' if cv.is_expired else 'no ':3}  "
                f"{'yes' if cv.embedding is not None else 'NO'}"
            )

        expired_count = sum(1 for cv in rows if cv.is_expired)
        no_emb_count  = sum(1 for cv in rows if cv.embedding is None)
        print(f"\n  Summary: {total} total · {expired_count} expired · {no_emb_count} missing embedding")


def section_chromadb() -> dict:
    print(f"\n{DIV2}")
    print("  2 · ChromaDB  —  collection 'cv_bank'")
    print(DIV2)

    col = vector_service._get_collection()
    if col is None:
        print("\n  ERROR: ChromaDB could not be initialised (check chroma_db/ path).\n")
        return {"col": None, "count": 0}

    count = col.count()
    meta  = col.metadata or {}

    print(f"\n  Total vectors : {count}")
    print(f"  Collection metadata:")
    if meta:
        for k, v in meta.items():
            print(f"    {k}: {v}")
    else:
        print("    (none)")

    # Peek at raw collection config if accessible
    try:
        cfg = col._model  # internal; varies by chromadb version
        if cfg:
            print(f"  Internal config : {cfg}")
    except Exception:
        pass

    return {"col": col, "count": count}


async def section_sample_query(chroma_count: int) -> None:
    print(f"\n{DIV2}")
    print(f"  3 · Sample query  —  \"{SAMPLE_QUERY}\"")
    print(DIV2)

    if chroma_count == 0:
        print("\n  Collection is empty — no query run.\n")
        return

    print("\n  Generating embedding via OpenAI…", end=" ", flush=True)
    try:
        embedding = await generate_embedding(SAMPLE_QUERY)
        print(f"OK  ({len(embedding)}-dim vector)\n")
    except Exception as exc:
        print(f"FAILED\n  ERROR: {exc}\n")
        return

    n = min(5, chroma_count)
    results = vector_service.search_similar(embedding, n_results=n)

    if not results:
        print("  No results returned from ChromaDB.\n")
        return

    print(f"  Top {len(results)} result(s) (cosine distance — lower = more similar):\n")
    print(f"  {'#':>2}  {'Distance':>8}  {'CV ID':36}  {'Filename':<34}  {'Hash[:16]':16}")
    print(f"  {DIV}")

    for i, r in enumerate(results, 1):
        meta     = r["metadata"] or {}
        filename = meta.get("filename", "—")
        if len(filename) > 34:
            filename = filename[:31] + "…"
        h = (meta.get("text_hash") or "")[:16]
        print(
            f"  {i:>2}  {r['distance']:>8.4f}  "
            f"{r['cv_id']:36}  "
            f"{filename:<34}  "
            f"{h or '—':16}"
        )

    print()


async def main() -> None:
    print(f"\n{DIV2}")
    print("  CV BANK DEBUG")
    print(DIV2)

    await section_postgres()
    info = section_chromadb()
    await section_sample_query(info["count"])


if __name__ == "__main__":
    asyncio.run(main())
