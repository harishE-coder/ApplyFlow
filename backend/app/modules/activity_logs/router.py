import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.activity_logs.models import ActivityLog

router = APIRouter(prefix="/api/activity-logs", tags=["activity-logs"])


class ActivityLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_role: str
    action: str
    details: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ActivityLogResponse])
async def list_activity_logs(
    user_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve activity audit logs (Admin sees all; Employee/Client sees own)."""
    query = (
        select(ActivityLog, User.name, User.role)
        .join(User, ActivityLog.user_id == User.id)
        .order_by(desc(ActivityLog.created_at))
    )

    if current_user.role != "admin":
        query = query.where(ActivityLog.user_id == current_user.id)
    elif user_id:
        query = query.where(ActivityLog.user_id == user_id)

    if action:
        query = query.where(ActivityLog.action == action)

    query = query.limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return [
        ActivityLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_name=uname,
            user_role=urole,
            action=log.action,
            details=log.details,
            created_at=log.created_at,
        )
        for log, uname, urole in rows
    ]
