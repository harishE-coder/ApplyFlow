"""
Security utilities: password hashing, JWT token creation/verification.
Uses HTTP-only cookies for token transport (more secure than localStorage).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

REVOKED_TOKENS: set[str] = set()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(user_id: UUID, role: str) -> str:
    """Create a short-lived access token (15 min default)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID, role: str) -> str:
    """Create a long-lived refresh token (7 days default)."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "exp": expire,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def revoke_token(token: str | None) -> None:
    """Invalidate a token and its JTI so it cannot be reused after logout."""
    if not token:
        return
    REVOKED_TOKENS.add(token)
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        if jti:
            REVOKED_TOKENS.add(jti)
    except Exception:
        pass


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    if not token or token in REVOKED_TOKENS:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        jti = payload.get("jti")
        if jti and jti in REVOKED_TOKENS:
            return None
        return payload
    except JWTError:
        return None
