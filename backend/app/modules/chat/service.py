import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, UploadFile

from app.modules.users.models import User, SubAdminAssignment
from app.modules.clients.models import Client, EmployeeClient
from app.modules.resumes.models import Resume
from app.modules.chat.models import ChatRoom, ChatMessage, ChatRead
from app.modules.notifications.models import Notification
from app.modules.chat.schemas import (
    ChatRoomResponse,
    ChatParticipant,
    ChatMessageResponse,
    MessageSender,
    ChatRoomsListResponse,
    ChatMessagesListResponse,
    UnreadCountResponse,
    ShareableResumeItem,
)
from app.modules.resumes.service import get_allowed_client_ids
from app.modules.users.service import get_sub_admin_client_ids, get_sub_admin_employee_ids
from app.services.google_drive import drive_service, UPLOAD_DIR


async def check_room_access(db: AsyncSession, user: User, room_id: uuid.UUID) -> ChatRoom:
    room = (
        await db.execute(
            select(ChatRoom)
            .where(ChatRoom.id == room_id)
            .options(selectinload(ChatRoom.client))
        )
    ).scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    allowed_cids = await get_allowed_client_ids(db, user)
    if allowed_cids is not None and room.client_id not in allowed_cids:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this client chat room")

    return room


async def get_or_create_room(db: AsyncSession, client_id: uuid.UUID) -> ChatRoom:
    room = (
        await db.execute(
            select(ChatRoom)
            .where(ChatRoom.client_id == client_id)
            .options(selectinload(ChatRoom.client))
        )
    ).scalar_one_or_none()

    if not room:
        room = ChatRoom(client_id=client_id, status="active")
        db.add(room)
        await db.flush()

    return room


async def get_rooms_for_user(db: AsyncSession, user: User) -> ChatRoomsListResponse:
    allowed = await get_allowed_client_ids(db, user)

    query = select(Client).order_by(Client.company_name)
    if allowed is not None:
        query = query.where(Client.id.in_(allowed))

    clients = (await db.execute(query)).scalars().all()

    rooms_out = []
    total_unread = 0

    for client in clients:
        room = await get_or_create_room(db, client.id)
        participants = await _get_room_participants(db, client.id)

        last_msg = (
            await db.execute(
                select(ChatMessage)
                .where(ChatMessage.room_id == room.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        unread = await _get_unread_count_for_room(db, user.id, room.id)
        total_unread += unread

        rooms_out.append(
            ChatRoomResponse(
                id=room.id,
                client_id=client.id,
                client_name=client.company_name,
                status=room.status,
                participants=participants,
                last_message=last_msg.message if last_msg else None,
                last_message_sender=last_msg.sender.name if last_msg and last_msg.sender else None,
                last_message_at=last_msg.created_at if last_msg else None,
                unread_count=unread,
            )
        )

    return ChatRoomsListResponse(items=rooms_out, total_unread=total_unread)


async def _get_room_participants(db: AsyncSession, client_id: uuid.UUID) -> list[ChatParticipant]:
    participants = []

    # 1. Admin
    admins = (await db.execute(select(User).where(User.role == "admin", User.is_active == True))).scalars().all()
    for a in admins:
        participants.append(ChatParticipant(id=a.id, name=a.name, role=a.role, is_primary=False))

    # 2. Assigned Sub-Admins
    sub_admin_assignments = (
        await db.execute(
            select(User)
            .join(SubAdminAssignment, SubAdminAssignment.sub_admin_id == User.id)
            .where(
                SubAdminAssignment.client_id == client_id,
                SubAdminAssignment.active == True,
                User.is_active == True,
            )
        )
    ).scalars().all()
    for sa in sub_admin_assignments:
        participants.append(ChatParticipant(id=sa.id, name=sa.name, role=sa.role, is_primary=False))

    # 3. Assigned Employees
    emp_assignments = (
        await db.execute(
            select(User, EmployeeClient.is_primary)
            .join(EmployeeClient, EmployeeClient.employee_id == User.id)
            .where(EmployeeClient.client_id == client_id, EmployeeClient.active == True, User.is_active == True)
        )
    ).all()
    for u, is_prim in emp_assignments:
        participants.append(ChatParticipant(id=u.id, name=u.name, role=u.role, is_primary=is_prim))

    # 4. Client Users
    client_users = (
        await db.execute(select(User).where(User.client_id == client_id, User.role == "client", User.is_active == True))
    ).scalars().all()
    for cu in client_users:
        participants.append(ChatParticipant(id=cu.id, name=cu.name, role=cu.role, is_primary=False))

    return participants


async def _get_unread_count_for_room(db: AsyncSession, user_id: uuid.UUID, room_id: uuid.UUID) -> int:
    read_record = (
        await db.execute(
            select(ChatRead).where(ChatRead.user_id == user_id, ChatRead.room_id == room_id)
        )
    ).scalar_one_or_none()

    if not read_record or not read_record.last_read_message_id:
        query = select(func.count(ChatMessage.id)).where(
            ChatMessage.room_id == room_id,
            ChatMessage.sender_id != user_id,
        )
        return (await db.execute(query)).scalar() or 0

    last_read_msg = (
        await db.execute(select(ChatMessage).where(ChatMessage.id == read_record.last_read_message_id))
    ).scalar_one_or_none()

    if not last_read_msg:
        query = select(func.count(ChatMessage.id)).where(
            ChatMessage.room_id == room_id,
            ChatMessage.sender_id != user_id,
        )
        return (await db.execute(query)).scalar() or 0

    query = select(func.count(ChatMessage.id)).where(
        ChatMessage.room_id == room_id,
        ChatMessage.sender_id != user_id,
        ChatMessage.created_at > last_read_msg.created_at,
    )
    return (await db.execute(query)).scalar() or 0


async def get_messages(
    db: AsyncSession, room_id: uuid.UUID, user: User, limit: int = 50, before_id: uuid.UUID | None = None
) -> ChatMessagesListResponse:
    await check_room_access(db, user, room_id)

    query = (
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id)
        .options(selectinload(ChatMessage.sender))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit + 1)
    )

    results = (await db.execute(query)).scalars().all()
    has_more = len(results) > limit
    messages = results[:limit]

    items = []
    for msg in reversed(messages):
        items.append(
            ChatMessageResponse(
                id=msg.id,
                room_id=msg.room_id,
                sender=MessageSender(id=msg.sender.id, name=msg.sender.name, role=msg.sender.role),
                message=msg.message,
                attachment_type=msg.attachment_type,
                attachment_reference=msg.attachment_reference,
                created_at=msg.created_at,
                edited_at=msg.edited_at,
            )
        )

    total = (await db.execute(select(func.count(ChatMessage.id)).where(ChatMessage.room_id == room_id))).scalar() or 0

    return ChatMessagesListResponse(items=items, has_more=has_more, total=total)


async def send_message(
    db: AsyncSession,
    room_id: uuid.UUID,
    user: User,
    text: str,
    attachment_type: str | None = None,
    attachment_reference: str | None = None,
    attachment_filename: str | None = None,
) -> ChatMessageResponse:
    room = await check_room_access(db, user, room_id)

    # Check read-only / inactive client state
    if room.status == "read_only" or (room.client and not room.client.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This chat room is read-only because the client account is inactive or locked.",
        )

    msg = ChatMessage(
        room_id=room_id,
        sender_id=user.id,
        message=text,
        attachment_type=attachment_type,
        attachment_reference=attachment_reference,
    )
    db.add(msg)
    await db.flush()

    await mark_read(db, room_id, user, msg.id)

    # Notifications
    participants = await _get_room_participants(db, room.client_id)
    client_name = room.client.company_name if room.client else "Chat"
    for p in participants:
        if p.id != user.id:
            db.add(
                Notification(
                    user_id=p.id,
                    title=f"New message in {client_name}",
                    message=f"{user.name}: {text[:100]}",
                    type="chat_message",
                )
            )

    return ChatMessageResponse(
        id=msg.id,
        room_id=msg.room_id,
        sender=MessageSender(id=user.id, name=user.name, role=user.role),
        message=msg.message,
        attachment_type=msg.attachment_type,
        attachment_reference=msg.attachment_reference,
        created_at=msg.created_at,
    )


async def share_resume(
    db: AsyncSession, room_id: uuid.UUID, user: User, resume_id: uuid.UUID
) -> ChatMessageResponse:
    room = await check_room_access(db, user, room_id)
    resume = (await db.execute(select(Resume).where(Resume.id == resume_id))).scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    text = f"📄 Shared Resume: {resume.candidate_name} ({resume.company} - {resume.role})"
    return await send_message(
        db, room_id, user, text, attachment_type="resume", attachment_reference=str(resume.id)
    )


async def mark_read(
    db: AsyncSession, room_id: uuid.UUID, user: User, message_id: uuid.UUID
) -> None:
    read_rec = (
        await db.execute(
            select(ChatRead).where(ChatRead.user_id == user.id, ChatRead.room_id == room_id)
        )
    ).scalar_one_or_none()

    if read_rec:
        read_rec.last_read_message_id = message_id
        read_rec.last_read_at = datetime.now(timezone.utc)
    else:
        read_rec = ChatRead(
            user_id=user.id,
            room_id=room_id,
            last_read_message_id=message_id,
            last_read_at=datetime.now(timezone.utc),
        )
        db.add(read_rec)

    await db.flush()


async def delete_message(db: AsyncSession, message_id: uuid.UUID, user: User) -> dict:
    msg = (await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if user.role != "admin" and msg.sender_id != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")

    room_id = str(msg.room_id)
    await db.delete(msg)
    await db.flush()
    return {"message": "Message deleted", "room_id": room_id}


async def lock_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> dict:
    room = await check_room_access(db, user, room_id)
    if user.role not in ("admin", "sub_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    room.status = "read_only"
    await db.flush()
    return {"message": "Chat room locked (read-only)"}


async def unlock_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> dict:
    room = await check_room_access(db, user, room_id)
    if user.role not in ("admin", "sub_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    room.status = "active"
    await db.flush()
    return {"message": "Chat room unlocked (active)"}


async def archive_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> dict:
    room = await check_room_access(db, user, room_id)
    if user.role not in ("admin", "sub_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    room.status = "archived"
    await db.flush()
    return {"message": "Chat room archived"}


async def export_room_chat(db: AsyncSession, room_id: uuid.UUID, user: User) -> list[dict]:
    room = await check_room_access(db, user, room_id)
    msgs = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .options(selectinload(ChatMessage.sender))
            .order_by(ChatMessage.created_at.asc())
        )
    ).scalars().all()

    return [
        {
            "id": str(m.id),
            "sender": m.sender.name,
            "role": m.sender.role,
            "message": m.message,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


async def get_total_unread(db: AsyncSession, user: User) -> UnreadCountResponse:
    rooms_res = await get_rooms_for_user(db, user)
    return UnreadCountResponse(total_unread=rooms_res.total_unread, unread_count=rooms_res.total_unread)
