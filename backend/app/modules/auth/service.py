"""
Auth service — business logic for authentication.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.activity_logs.models import ActivityLog
from app.modules.users.models import User


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """
    Validate email and password.
    Returns User if valid, None if invalid.
    """
    from sqlalchemy import func
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.strip().lower(), User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # For client users: check if their company is active
    if user.role == "client" and user.client_id:
        from app.modules.clients.models import Client
        client_res = await db.execute(select(Client).where(Client.id == user.client_id))
        client = client_res.scalar_one_or_none()
        if client and (not client.is_active or client.status in ("inactive", "archived")):
            return None

    return user


async def log_activity(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    details: dict | None = None,
) -> None:
    """Record an activity log entry."""
    log = ActivityLog(
        user_id=user_id,
        action=action,
        details=details,
    )
    db.add(log)
    # Don't commit here — let the request lifecycle handle it
