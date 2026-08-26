"""
Chat REST API router.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.chat import service
from app.modules.chat.schemas import (
    SendMessageRequest, ShareResumeRequest, MarkReadRequest,
    ChatRoomsListResponse, ChatMessagesListResponse, UnreadCountResponse,
    ChatMessageResponse, ShareableResumeItem,
)
from app.modules.chat.websocket import manager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.get("/rooms", response_model=ChatRoomsListResponse)
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all chat rooms accessible by the current user."""
    return await service.get_rooms_for_user(db, current_user)


@router.get("/rooms/{room_id}/messages", response_model=ChatMessagesListResponse)
async def get_room_messages(
    room_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get paginated messages for a chat room."""
    return await service.get_messages(db, room_id, current_user, limit, before_id)


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    room_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Send a text message to a chat room."""
    res = await service.send_message(
        db, room_id, current_user,
        body.message,
        attachment_type=body.attachment_type,
        attachment_reference=body.attachment_reference,
        attachment_filename=body.attachment_filename,
    )
    # Broadcast to WebSocket connections
    await manager.broadcast(str(room_id), {
        "type": "new_message",
        "message": res.model_dump(mode="json"),
    })
    return res


@router.post("/rooms/{room_id}/share-resume", response_model=ChatMessageResponse)
async def share_resume(
    room_id: UUID,
    body: ShareResumeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Share a resume into a chat room."""
    res = await service.share_resume(db, room_id, current_user, body.resume_id)
    # Broadcast to WebSocket connections
    await manager.broadcast(str(room_id), {
        "type": "new_message",
        "message": res.model_dump(mode="json"),
    })
    return res


@router.patch("/rooms/{room_id}/read")
@router.post("/rooms/{room_id}/read")
async def mark_read(
    room_id: UUID,
    body: MarkReadRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark messages as read up to a specific message or all."""
    await service.check_room_access(db, current_user, room_id)
    msg_id = body.message_id if body else None
    await service.mark_read(db, room_id, current_user, msg_id)
    # Broadcast read receipt
    await manager.broadcast(str(room_id), {
        "type": "read_receipt",
        "user_id": str(current_user.id),
        "user_name": current_user.name,
        "message_id": str(msg_id) if msg_id else None,
    }, exclude_user=str(current_user.id))
    return {"success": True}


@router.post("/rooms/{room_id}/lock")
async def lock_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lock room into read-only mode."""
    return await service.lock_room(db, room_id, current_user)


@router.post("/rooms/{room_id}/unlock")
async def unlock_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Unlock room into active mode."""
    return await service.unlock_room(db, room_id, current_user)


@router.post("/rooms/{room_id}/archive")
async def archive_room(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Archive chat room."""
    return await service.archive_room(db, room_id, current_user)


@router.get("/rooms/{room_id}/export")
async def export_room_chat(
    room_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export room chat transcript."""
    return await service.export_room_chat(db, room_id, current_user)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a chat message."""
    res = await service.delete_message(db, message_id, current_user)
    if "room_id" in res:
        await manager.broadcast(res["room_id"], {
            "type": "message_deleted",
            "message_id": str(message_id),
        })
    return res


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get total unread message count across all accessible rooms."""
    return await service.get_total_unread(db, current_user)
