"""
Auth router — login, refresh, logout, and current user endpoints.
Tokens are set as HTTP-only cookies for security.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.auth.schemas import AuthResponse, LoginRequest, RefreshResponse, UserResponse
from app.modules.auth.service import authenticate_user, log_activity

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user) -> None:
    """Set access and refresh tokens as HTTP-only cookies."""
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set True in production with HTTPS
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",  # Only sent to auth endpoints
    )


import time
import asyncio
from app.core.dependencies import _user_cache
from app.modules.dashboard.service import warm_user_dashboard

@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user, set JWT cookies, cache user, and pre-warm dashboard in background."""
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _set_auth_cookies(response, user)
    await log_activity(db, user.id, "login")

    # Immediate cache population & background dashboard pre-warming
    _user_cache[str(user.id)] = (
        time.time() + 60.0,
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
    asyncio.create_task(warm_user_dashboard(user.id, user.role, user.email))

    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh the access token using the refresh token cookie."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    from uuid import UUID
    from sqlalchemy import select
    from app.modules.users.models import User

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    _set_auth_cookies(response, user)
    return RefreshResponse()


@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookies."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Return currently authenticated user from cookie."""
    return UserResponse.model_validate(current_user)


@router.get("/bootstrap")
async def get_app_bootstrap(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Unified Application Bootstrap Endpoint:
    Returns user profile, dashboard telemetry, notification items, and chat unread count
    in 1 single ultra-fast roundtrip.
    """
    from app.modules.dashboard.service import get_admin_dashboard_home, get_employee_dashboard_home, get_client_dashboard_home
    from app.modules.notifications.service import get_user_notifications
    from app.modules.chat.service import get_total_unread

    async def fetch_dash():
        if current_user.role in ("admin", "sub_admin"):
            return await get_admin_dashboard_home(db, current_user=current_user, date_range="today")
        elif current_user.role == "employee":
            return await get_employee_dashboard_home(db, current_user=current_user, date_range="today")
        else:
            return await get_client_dashboard_home(db, current_user=current_user)

    dash_data = await fetch_dash()
    notif_data = await get_user_notifications(db, current_user, limit=20)
    chat_unread = await get_total_unread(db, current_user)

    return {
        "user": UserResponse.model_validate(current_user),
        "dashboard": dash_data,
        "notifications": notif_data,
        "chat_unread": chat_unread,
    }
