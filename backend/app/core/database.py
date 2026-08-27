"""
Async SQLAlchemy database engine, session factory, base model, and query profiler hooks.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.profiler import record_sql_start, record_sql_end


def _create_engine():
    url = settings.database_url
    if "sqlite" in url:
        eng = create_async_engine(
            url,
            echo=False,
        )
    else:
        eng = create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=15,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=30,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "command_timeout": 30,
                "timeout": 30,
                "server_settings": {
                    "jit": "off",
                    "application_name": "applyflow_api",
                },
            },
        )

    # Attach profiler listeners to sync_engine
    @event.listens_for(eng.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        record_sql_start()

    @event.listens_for(eng.sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        record_sql_end()

    return eng


engine = _create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def warmup_db_pool():
    """Pre-warm database connections on server startup."""
    try:
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        print("⚡ Database connection pool warmed and ready.")
    except Exception as e:
        print(f"⚠️ Note during DB pool warmup: {e}")


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
