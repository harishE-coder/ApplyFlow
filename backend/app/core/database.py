"""
Async SQLAlchemy database engine, session factory, and base model.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

def _create_engine():
    url = settings.database_url
    if "sqlite" in url:
        return create_async_engine(
            url,
            echo=False,
        )
    return create_async_engine(
        url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

engine = _create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)



class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
