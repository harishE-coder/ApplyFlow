"""
Web Push Notification Service for ApplyFlow Chat (v1.1).
Handles payload signing with VAPID, room presence suppression,
Redis SETNX deduplication, user preferences, offline unread count badge,
reliable retry queue (429/5xx), and expired subscription auto-cleanup (410/404).
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import settings
from app.core.database import async_session_factory
from app.modules.chat.models import ChatMessage, ChatRead, ChatRoom, PushSubscription
from app.modules.chat.websocket import manager
from app.modules.clients.models import EmployeeClient
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import SubAdminAssignment, User

logger = logging.getLogger(__name__)

# Telemetry tracking for admin monitoring
_push_stats: dict[str, int] = {
    "total_sent": 0,
    "failed_pushes": 0,
    "cleaned_subscriptions": 0,
    "retried_pushes": 0,
}


import time


def get_push_stats() -> dict[str, int]:
    """Returns a snapshot of in-memory push statistics."""
    return _push_stats.copy()


def enqueue_push_retry(
    subscription_id: uuid.UUID | str,
    room_id: uuid.UUID | str,
    message_id: uuid.UUID | str,
    payload: dict[str, Any],
    attempt: int = 1,
    delay_seconds: int = 60,
) -> None:
    """Enqueues a failed push notification into persistent Redis / Cache retry queue."""
    retry_job = {
        "subscription_id": str(subscription_id),
        "room_id": str(room_id),
        "message_id": str(message_id),
        "payload": payload,
        "attempt": attempt,
        "next_retry": int(time.time()) + delay_seconds,
    }
    cache.rpush("push:retry_queue", retry_job)
    logger.info(f"Enqueued push retry job for subscription {subscription_id} (Attempt {attempt}).")


async def process_push_retry_queue(db: AsyncSession) -> int:
    """
    Worker consumer: processes pending push retry jobs from Redis / Cache.
    Survives application restarts and works across all workers.
    """
    jobs = cache.lrange("push:retry_queue")
    if not jobs:
        return 0

    now = int(time.time())
    processed_count = 0

    for job in list(jobs):
        if not isinstance(job, dict):
            continue
        if job.get("next_retry", 0) > now:
            continue

        cache.lrem("push:retry_queue", 1, job)
        sub_id = job.get("subscription_id")
        try:
            sub = (
                await db.execute(
                    select(PushSubscription).where(PushSubscription.id == uuid.UUID(sub_id))
                )
            ).scalar_one_or_none()

            if not sub:
                continue

            success = await send_push_notification(
                db, sub, job.get("payload", {}), retry_delays=[0]
            )
            if not success and job.get("attempt", 1) < 4:
                # Requeue with higher delay
                enqueue_push_retry(
                    subscription_id=sub_id,
                    room_id=job.get("room_id", ""),
                    message_id=job.get("message_id", ""),
                    payload=job.get("payload", {}),
                    attempt=job.get("attempt", 1) + 1,
                    delay_seconds=120,
                )
            processed_count += 1
        except Exception as err:
            logger.error(f"Error processing push retry job {job}: {err}")

    return processed_count


async def get_admin_push_telemetry(db: AsyncSession) -> dict[str, Any]:
    """Provides aggregated admin oversight metrics without exposing endpoints, auth keys, or private IDs."""
    subs_count = (await db.execute(select(func.count(PushSubscription.id)))).scalar() or 0
    active_rooms = len(manager.room_connections)
    active_users = len(manager.user_connections)
    pending_retries = len(cache.lrange("push:retry_queue"))

    return {
        "status": "healthy" if settings.vapid_public_key and settings.vapid_private_key else "unconfigured",
        "online_users": active_users,
        "active_rooms": active_rooms,
        "subscriptions": subs_count,
        "total_sent": _push_stats["total_sent"],
        "failed_today": _push_stats["failed_pushes"],
        "retried_pushes": _push_stats["retried_pushes"],
        "retries_pending": pending_retries,
        "cleaned_subscriptions": _push_stats["cleaned_subscriptions"],
        "vapid_configured": bool(settings.vapid_public_key and settings.vapid_private_key),
    }


async def send_push_notification(
    db: AsyncSession,
    subscription: PushSubscription,
    payload: dict[str, Any],
    retry_delays: list[float] | None = None,
) -> bool:
    """
    Sends a Web Push notification to a single browser subscription endpoint with exponential retry
    and persistent queue fallback.
    """
    if not settings.vapid_private_key or not settings.vapid_public_key:
        logger.debug("VAPID keys not configured, skipping web push dispatch.")
        return False

    sub_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }
    claims = {"sub": settings.vapid_email}
    data_str = json.dumps(payload)

    # Retry schedule: Attempt 1 (immediate), Attempt 2 (5s), Attempt 3 (15s), Attempt 4 (60s)
    delays = retry_delays if retry_delays is not None else [0, 5, 15, 60]

    for attempt, delay in enumerate(delays):
        if delay > 0:
            _push_stats["retried_pushes"] += 1
            logger.debug(f"Retrying web push in {delay}s (Attempt {attempt + 1}/{len(delays)})...")
            await asyncio.sleep(delay)

        try:
            webpush(
                subscription_info=sub_info,
                data=data_str,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims=claims,
                ttl=86400,
            )
            _push_stats["total_sent"] += 1
            return True
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None) if getattr(exc, "response", None) else None
            err_msg = str(exc).lower()

            # 410 / 404 -> Permanent Gone / Unsubscribed: Delete from DB immediately
            if status_code in (404, 410) or "unsubscribed" in err_msg or "expired" in err_msg or "gone" in err_msg:
                logger.info(
                    f"Push subscription {subscription.id} for user {subscription.user_id} expired/gone ({status_code or exc}). Deleting from DB."
                )
                _push_stats["cleaned_subscriptions"] += 1
                try:
                    await db.delete(subscription)
                    await db.commit()
                except Exception as del_err:
                    logger.error(f"Failed to delete expired subscription {subscription.id}: {del_err}")
                return False

            # 401 / 403 -> Authentication / Authorization failure: Do not retry
            if status_code in (401, 403):
                _push_stats["failed_pushes"] += 1
                logger.warning(f"WebPush authorization error ({status_code}) for endpoint {subscription.endpoint[:40]}. Not retrying.")
                return False

            # 429 & 5xx (500, 502, 503, 504) -> Temporary failure: Eligible for retry
            if status_code in (429, 500, 502, 503, 504) or status_code is None:
                if attempt < len(delays) - 1:
                    logger.warning(f"Temporary WebPush failure ({status_code or 'network error'}). Will retry...")
                    continue
                else:
                    # Enqueue to persistent queue
                    enqueue_push_retry(
                        subscription_id=subscription.id,
                        room_id=payload.get("room_id", ""),
                        message_id=payload.get("message_id", ""),
                        payload=payload,
                        attempt=attempt + 1,
                        delay_seconds=60,
                    )

            _push_stats["failed_pushes"] += 1
            logger.warning(f"WebPush failed for endpoint {subscription.endpoint[:40]}... (Status {status_code}): {exc}")
            return False
        except Exception as exc:
            if attempt < len(delays) - 1:
                logger.warning(f"Unexpected WebPush network error: {exc}. Will retry...")
                continue

            _push_stats["failed_pushes"] += 1
            logger.warning(f"Unexpected error sending webpush: {exc}")
            return False

    return False



async def notify_room_recipients(
    room_id: uuid.UUID | str,
    sender_id: uuid.UUID | str | None,
    sender_name: str,
    message_id: uuid.UUID | str,
    preview_text: str,
    attachment_type: str | None = None,
    created_at: datetime | None = None,
) -> int:
    """
    Finds all eligible recipients of a chat room, checks room-aware presence and preferences,
    calculates offline unread count per recipient, deduplicates per message_id/user_id,
    and sends Web Push notifications with retry.
    """
    room_uuid = uuid.UUID(str(room_id)) if isinstance(room_id, str) else room_id
    sender_uuid = uuid.UUID(str(sender_id)) if sender_id and isinstance(sender_id, str) else sender_id
    room_id_str = str(room_uuid)
    msg_id_str = str(message_id)

    async with async_session_factory() as db:
        room = (
            await db.execute(
                select(ChatRoom).where(ChatRoom.id == room_uuid)
            )
        ).scalar_one_or_none()

        if not room:
            return 0

        client_id = room.client_id
        recipient_ids: set[uuid.UUID] = set()

        # 1. Super Admins
        admins = (
            await db.execute(
                select(User.id).where(User.role == "admin", User.is_active == True)
            )
        ).scalars().all()
        recipient_ids.update(admins)

        # 2. Sub-Admins assigned to client
        sub_admins = (
            await db.execute(
                select(SubAdminAssignment.sub_admin_id)
                .join(User, SubAdminAssignment.sub_admin_id == User.id)
                .where(
                    SubAdminAssignment.client_id == client_id,
                    SubAdminAssignment.active == True,
                    User.is_active == True,
                )
            )
        ).scalars().all()
        recipient_ids.update(sub_admins)

        # 3. Employees assigned to client
        employees = (
            await db.execute(
                select(EmployeeClient.employee_id)
                .join(User, EmployeeClient.employee_id == User.id)
                .where(
                    EmployeeClient.client_id == client_id,
                    EmployeeClient.active == True,
                    User.is_active == True,
                )
            )
        ).scalars().all()
        recipient_ids.update(employees)

        # 4. Client Users
        client_users = (
            await db.execute(
                select(User.id).where(
                    User.role == "client",
                    User.client_id == client_id,
                    User.is_active == True,
                )
            )
        ).scalars().all()
        recipient_ids.update(client_users)

        # Exclude sender
        if sender_uuid:
            recipient_ids.discard(sender_uuid)

        if not recipient_ids:
            return 0

        # Query user preferences
        prefs_res = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id.in_(list(recipient_ids))
            )
        )
        prefs_map = {p.user_id: p for p in prefs_res.scalars().all()}

        # Build base preview text
        preview = preview_text or ""
        if attachment_type:
            preview = f"[{attachment_type.upper()}] {preview}".strip()

        sent_count = 0

        for recipient_id in recipient_ids:
            rec_id_str = str(recipient_id)

            # Check 1: Is user currently active inside the EXACT same room?
            if manager.is_user_in_room(rec_id_str, room_id_str):
                logger.debug(f"Recipient {rec_id_str} is actively viewing room {room_id_str}. Suppressing push.")
                continue

            # Check 2: Notification Preferences
            pref = prefs_map.get(recipient_id)
            if pref:
                if not pref.chat_push:
                    continue
                if room_id_str in (pref.muted_rooms or []):
                    continue

            # Check 3: Notification Deduplication (Redis/Cache SETNX)
            dedup_key = f"push:{msg_id_str}:{rec_id_str}"
            is_new = cache.set_nx(dedup_key, "1", ttl=30)
            if not is_new:
                logger.debug(f"Duplicate push prevented for {dedup_key}")
                continue

            # Check 4: Calculate offline unread count for this recipient in this room
            read_rec = (await db.execute(
                select(ChatRead).where(ChatRead.user_id == recipient_id, ChatRead.room_id == room_uuid)
            )).scalar_one_or_none()

            count_q = select(func.count(ChatMessage.id)).where(
                ChatMessage.room_id == room_uuid,
                ChatMessage.sender_id != recipient_id,
            )
            if read_rec and read_rec.last_read_at:
                count_q = count_q.where(ChatMessage.created_at > read_rec.last_read_at)

            unread_cnt = (await db.execute(count_q)).scalar() or 1

            # Build enriched payload with unread_count badge
            payload = {
                "type": "chat_message",
                "room_id": room_id_str,
                "message_id": msg_id_str,
                "sender_name": sender_name,
                "preview": preview[:200],
                "unread_count": unread_cnt,
                "sent_at": (created_at or datetime.now(timezone.utc)).isoformat(),
            }

            # Query recipient subscriptions
            subs_res = await db.execute(
                select(PushSubscription).where(PushSubscription.user_id == recipient_id)
            )
            subs = subs_res.scalars().all()
            if not subs:
                continue

            for sub in subs:
                success = await send_push_notification(db, sub, payload)
                if success:
                    sent_count += 1

        return sent_count
