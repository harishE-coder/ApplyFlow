"""
FastAPI dependencies for authentication and authorization.
Reads JWT from HTTP-only cookies (not Authorization header).
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token


import time

_user_cache: dict[str, tuple[float, any]] = {}

def invalidate_user_cache(user_id: UUID | str):
    """Invalidate cached user when updated."""
    _user_cache.pop(str(user_id), None)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Extract and validate the access token from HTTP-only cookie.
    Returns the User ORM object with short-lived memory caching to prevent
    redundant database round-trips on concurrent frontend component requests.
    """
    # Import here to avoid circular imports
    from app.modules.users.models import User

    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fast memory cache check
    cached = _user_cache.get(str(user_id))
    if cached:
        cached_expires, user_dict = cached
        if time.time() < cached_expires:
            u = User(
                id=user_dict["id"],
                name=user_dict["name"],
                email=user_dict["email"],
                role=user_dict["role"],
                client_id=user_dict.get("client_id"),
                is_active=user_dict.get("is_active", True),
                phone=user_dict.get("phone"),
                status=user_dict.get("status", "active"),
            )
            return u
        else:
            _user_cache.pop(str(user_id), None)

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Cache user dict for 30 seconds
    _user_cache[str(user_id)] = (
        time.time() + 30.0,
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "client_id": user.client_id,
            "is_active": user.is_active,
            "phone": getattr(user, "phone", None),
            "status": getattr(user, "status", "active"),
        },
    )

    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory: restricts endpoint to specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not permitted. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
