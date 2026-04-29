"""Rebuild the ChromaDB vector store from embeddings stored in MySQL.

Reads every non-expired CV that has an embedding in the cvs table and
upserts it into the ChromaDB collection.  Safe to run multiple times —
ChromaDB upsert is idempotent (same id = replace, not duplicate).

Usage:
    python -m core.scripts.rebuild_chroma
"""

import asyncio
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

from core.db.database import AsyncSessionLocal
from core.db.models import CV
from core.services import vector_service

DIV = "=" * 72


async def main() -> None:
    print(f"\n{DIV}")
    print("  REBUILD CHROMADB  —  repopulate from MySQL embeddings")
    print(DIV)

    # ── 1. Get ChromaDB collection ────────────────────────────────────────
    col = vector_service._get_collection()
    if col is None:
        print("\n  ERROR: ChromaDB could not be initialised. Aborting.\n")
        sys.exit(1)

    before = col.count()
    print(f"\n  ChromaDB vectors before rebuild : {before}")

    # ── 2. Fetch all CVs with embeddings from MySQL ───────────────────────
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(CV).where(CV.embedding.is_not(None))
            )
        ).scalars().all()

    total      = len(rows)
    expired    = sum(1 for cv in rows if cv.is_expired)
    active     = total - expired

    print(f"  MySQL CVs with embedding        : {total} ({active} active, {expired} expired)")

    if total == 0:
        print("\n  Nothing to rebuild. Upload CVs first via /cvs/batch or /analyze.\n")
        return

    # ── 3. Upsert each CV into ChromaDB ───────────────────────────────────
    print(f"\n  Upserting {total} vector(s)…\n")

    ok = skipped = failed = 0
    for cv in rows:
        try:
            metadata = {
                "filename"    : cv.filename,
                "text_hash"   : cv.text_hash,
                "last_seen_at": cv.last_seen_at.isoformat() if cv.last_seen_at else "",
                "is_expired"  : cv.is_expired,
                "times_matched": cv.times_matched,
                "created_at"  : cv.created_at.isoformat() if cv.created_at else "",
            }
            vector_service.add_cv(
                cv_id    =str(cv.id),
                text     =cv.text_content,
                embedding=cv.embedding,
                metadata =metadata,
            )
            status = "EXPIRED" if cv.is_expired else "OK"
            fname  = cv.filename[:50] + "..." if len(cv.filename) > 50 else cv.filename
            print(f"  [{status:7}]  {str(cv.id)}  {fname}")
            ok += 1
        except Exception as exc:
            print(f"  [FAILED ]  {str(cv.id)}  {cv.filename[:50]}  — {exc}")
            failed += 1

    # ── 4. Summary ────────────────────────────────────────────────────────
    after = col.count()
    print(f"\n{DIV}")
    print(f"  Done.  Upserted: {ok}  Failed: {failed}  Skipped: {skipped}")
    print(f"  ChromaDB vectors before: {before}  →  after: {after}")
    if after == active:
        print(f"  Counts match — ChromaDB is in sync with MySQL active CVs.")
    else:
        diff = active - after
        print(f"  WARNING: {diff} active CV(s) still missing from ChromaDB.")
    print(DIV + "\n")


if __name__ == "__main__":
    asyncio.run(main())
