"""
Auth Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    client_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Returned on login — tokens are set as HTTP-only cookies, not in body."""
    user: UserResponse
    message: str = "Login successful"


class RefreshResponse(BaseModel):
    message: str = "Token refreshed"
