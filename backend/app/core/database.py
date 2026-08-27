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
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=60,
        pool_timeout=30,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "command_timeout": 60,
            "server_settings": {"jit": "off"},
        },
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


# Ensure all models are imported into SQLAlchemy registry
def _import_all_models():
    try:
        import app.modules.users.models  # noqa: F401
        import app.modules.clients.models  # noqa: F401
        import app.modules.requirements.models  # noqa: F401
        import app.modules.resumes.models  # noqa: F401
        import app.modules.applications.models  # noqa: F401
        import app.modules.targets.models  # noqa: F401
        import app.modules.attendance.models  # noqa: F401
        import app.modules.notifications.models  # noqa: F401
        import app.modules.activity_logs.models  # noqa: F401
        import app.modules.chat.models  # noqa: F401
    except Exception:
        pass

_import_all_models()


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
