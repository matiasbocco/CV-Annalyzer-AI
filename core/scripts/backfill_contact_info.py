"""
Backfill contact info for CVs that predate the contact-extraction feature.

Run as:
    python -m core.scripts.backfill_contact_info
"""

import asyncio
import sys

from sqlalchemy import select

from core.db.database import AsyncSessionLocal
from core.db.models import CV
from core.services.contact_service import extract_contact_info


async def backfill() -> None:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(CV)
                .where(CV.contact_extracted_at.is_(None))
                .order_by(CV.created_at)
            )
        ).scalars().all()

    total = len(rows)
    if total == 0:
        print("Nothing to backfill — all CVs already have contact info.")
        return

    print(f"Found {total} CV(s) without contact info. Starting extraction...\n")

    updated = 0
    failed  = 0

    for i, cv in enumerate(rows, 1):
        print(f"  Processing {i}/{total}: {cv.filename}...", end=" ", flush=True)
        try:
            contact = await extract_contact_info(cv.text_content)
            async with AsyncSessionLocal() as db:
                row = await db.get(CV, cv.id)
                if row is None:
                    print("skipped (deleted)")
                    continue
                from datetime import datetime, timezone
                row.full_name            = contact.get("full_name")
                row.email                = contact.get("email")
                row.phone                = contact.get("phone")
                row.linkedin_url         = contact.get("linkedin_url")
                row.github_url           = contact.get("github_url")
                row.portfolio_url        = contact.get("portfolio_url")
                row.location             = contact.get("location")
                row.availability         = contact.get("availability")
                row.contact_extracted_at = datetime.now(timezone.utc)
                await db.commit()
            name_hint = contact.get("full_name") or "(no name extracted)"
            print(f"done  [{name_hint}]")
            updated += 1
        except Exception as exc:
            print(f"FAILED  [{exc}]")
            failed += 1

    print(f"\nBackfill complete: {updated} updated, {failed} failed.")


def main() -> None:
    sys.exit(asyncio.run(backfill()))


if __name__ == "__main__":
    main()
