from collections.abc import AsyncIterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync engine for Celery tasks. Celery workers run synchronous task functions
# (no running event loop), so they need pymysql instead of aiomysql. The tasks
# use asyncio.run() to bridge into async service code, which uses the async
# engine above — this sync engine is available as a fallback for simple sync
# DB access outside the async pipeline.
sync_engine = create_engine(
    settings.database_url.replace("mysql+aiomysql", "mysql+pymysql"),
    echo=False,
    future=True,
)
SyncSessionLocal = sessionmaker(sync_engine)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
