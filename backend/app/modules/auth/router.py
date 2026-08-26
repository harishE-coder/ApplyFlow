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


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and set JWT cookies."""
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _set_auth_cookies(response, user)
    await log_activity(db, user.id, "login")

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
    """Get the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
