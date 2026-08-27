import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.modules.users.models import User
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationResponse, NotificationListResponse


from app.core.cache import cache, invalidate_notifications_cache


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str = "info",
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
    )
    db.add(notif)
    await db.flush()
    invalidate_notifications_cache()
    return notif


async def get_user_notifications(
    db: AsyncSession, user: User, limit: int = 20
) -> NotificationListResponse:
    cache_key = f"notif:{str(user.id)}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        print(f"\033[92m[CACHE HIT] Notifications ({cache_key})\033[0m")
        return cached

    query = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    unread_count = sum(1 for n in items if not n.is_read)

    resp = NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        unread_count=unread_count,
    )
    cache.set(cache_key, resp, ttl=15.0, tags={"notifications"})
    return resp


async def mark_as_read(db: AsyncSession, user: User, notification_id: uuid.UUID) -> bool:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user.id)
        .values(is_read=True)
    )
    await db.flush()
    invalidate_notifications_cache()
    return True


async def mark_all_as_read(db: AsyncSession, user: User) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.flush()
    invalidate_notifications_cache()
    return result.rowcount


async def delete_notification(db: AsyncSession, user: User, notification_id: uuid.UUID) -> None:
    notif = (
        await db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notif)
    await db.flush()


async def clear_old_notifications(db: AsyncSession, user: User, days: int = 30) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        delete(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read == True,
            Notification.created_at < cutoff,
        )
    )
    await db.flush()
    return result.rowcount
