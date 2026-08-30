"""Seed script to create initial organization and admin user.

Run this script after running the database migrations:
    python -m core.scripts.seed_admin

This script is idempotent - it's safe to run multiple times.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.database import AsyncSessionLocal
from core.db.models import Organization, User, UserRole
from core.services.auth_service import hash_password


async def seed_admin():
    """Create the default organization and admin user if they don't exist."""
    async with AsyncSessionLocal() as db:
        # Check if organization already exists
        result = await db.execute(
            select(Organization).where(Organization.name == "CV Analyzer")
        )
        org = result.scalar_one_or_none()

        if org is None:
            # Create organization
            org = Organization(name="CV Analyzer")
            db.add(org)
            await db.flush()  # Get the org ID before committing
            print(f"[CREATED] Organization: {org.name} (ID: {org.id})")
        else:
            print(f"[EXISTS] Organization: {org.name} (ID: {org.id})")

        # Check if admin user already exists
        admin_email = "admin@cvanalyzer.com"
        result = await db.execute(select(User).where(User.email == admin_email))
        admin_user = result.scalar_one_or_none()

        if admin_user is None:
            # Create admin user
            admin_password = "Admin1234!"
            admin_user = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                role=UserRole.admin,
                first_name="Admin",
                last_name="Sistema",
                organization_id=org.id,
                is_active=True,
                must_change_password=True,
            )
            db.add(admin_user)
            await db.commit()

            print(f"[CREATED] Admin user: {admin_email}")
            print("")
            print("=" * 60)
            print("ADMIN CREDENTIALS")
            print("=" * 60)
            print(f"Email:    {admin_email}")
            print(f"Password: {admin_password}")
            print("")
            print("⚠️  IMPORTANT: Change this password immediately after first login!")
            print("=" * 60)
        else:
            print(f"[EXISTS] Admin user: {admin_email} (ID: {admin_user.id})")
            print("")
            print("Admin user already exists. No changes made.")


if __name__ == "__main__":
    print("Running admin seed script...")
    print("")
    asyncio.run(seed_admin())
    print("")
    print("Seed script completed successfully!")
