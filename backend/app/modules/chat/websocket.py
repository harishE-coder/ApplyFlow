"""
Chat WebSocket endpoint for real-time messaging.
Handles message broadcasting, typing indicators, read receipts, and presence.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import decode_token
from app.modules.users.models import User
from app.modules.chat.models import ChatRoom, ChatMessage, ChatRead
from app.modules.clients.models import EmployeeClient

router = APIRouter()


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections per room."""

    def __init__(self):
        # room_id -> {user_id: WebSocket}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        # user_id -> user info
        self.user_info: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str, user_role: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
        self.user_info[user_id] = {"name": user_name, "role": user_role}

        # Broadcast presence
        await self.broadcast(room_id, {
            "type": "presence",
            "user_id": user_id,
            "user_name": user_name,
            "status": "online",
            "online_users": list(self.active_connections.get(room_id, {}).keys()),
        }, exclude_user=None)

    def disconnect(self, room_id: str, user_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].pop(user_id, None)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict, exclude_user: str | None = None):
        """Send message to all connected clients in a room."""
        if room_id not in self.active_connections:
            return
        dead = []
        for uid, ws in self.active_connections[room_id].items():
            if uid == exclude_user:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.active_connections[room_id].pop(uid, None)

    def get_online_users(self, room_id: str) -> list[str]:
        return list(self.active_connections.get(room_id, {}).keys())


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def authenticate_ws(websocket: WebSocket) -> User | None:
    """Authenticate WebSocket via cookie or token query parameter."""
    token = websocket.cookies.get("access_token") or websocket.query_params.get("token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id), User.is_active == True)  # noqa: E712
        )
        return result.scalar_one_or_none()


async def check_ws_room_access(user: User, room_id: uuid.UUID) -> bool:
    """Check if user has access to the room."""
    async with async_session_factory() as db:
        room = (await db.execute(
            select(ChatRoom).where(ChatRoom.id == room_id)
        )).scalar_one_or_none()
        if not room:
            return False

        if user.role == "admin":
            return True
        elif user.role == "sub_admin":
            from app.modules.users.service import get_sub_admin_client_ids
            allowed_cids = await get_sub_admin_client_ids(db, user.id)
            return room.client_id in allowed_cids
        elif user.role == "employee":
            result = await db.execute(
                select(EmployeeClient).where(
                    EmployeeClient.employee_id == user.id,
                    EmployeeClient.client_id == room.client_id,
                    EmployeeClient.active == True,  # noqa: E712
                )
            )
            return result.scalar_one_or_none() is not None
        elif user.role == "client":
            return user.client_id == room.client_id
        return False


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/chat/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time chat."""
    user = await authenticate_ws(websocket)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    room_uuid = uuid.UUID(room_id)
    if not await check_ws_room_access(user, room_uuid):
        await websocket.close(code=4003, reason="Access denied")
        return

    user_id_str = str(user.id)
    await manager.connect(websocket, room_id, user_id_str, user.name, user.role)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                # Save message to DB
                text = data.get("text", "").strip()
                if not text:
                    continue

                async with async_session_factory() as db:
                    msg = ChatMessage(
                        room_id=room_uuid,
                        sender_id=user.id,
                        message=text,
                    )
                    db.add(msg)

                    # Auto-mark read for sender
                    read_record = (await db.execute(
                        select(ChatRead).where(
                            ChatRead.user_id == user.id,
                            ChatRead.room_id == room_uuid,
                        )
                    )).scalar_one_or_none()
                    if read_record:
                        read_record.last_read_message_id = msg.id
                        read_record.read_at = datetime.now(timezone.utc)
                    else:
                        db.add(ChatRead(
                            user_id=user.id,
                            room_id=room_uuid,
                            last_read_message_id=msg.id,
                        ))

                    await db.commit()

                    # Broadcast to all in room
                    await manager.broadcast(room_id, {
                        "type": "new_message",
                        "message": {
                            "id": str(msg.id),
                            "room_id": room_id,
                            "sender": {
                                "id": user_id_str,
                                "name": user.name,
                                "role": user.role,
                            },
                            "message": text,
                            "attachment_type": None,
                            "attachment_reference": None,
                            "created_at": msg.created_at.isoformat() if msg.created_at else datetime.now(timezone.utc).isoformat(),
                            "is_deleted": False,
                        },
                    })

            elif msg_type == "typing":
                await manager.broadcast(room_id, {
                    "type": "typing",
                    "user_id": user_id_str,
                    "user_name": user.name,
                    "is_typing": data.get("is_typing", True),
                }, exclude_user=user_id_str)

            elif msg_type == "read":
                message_id = data.get("message_id")
                if message_id:
                    async with async_session_factory() as db:
                        read_record = (await db.execute(
                            select(ChatRead).where(
                                ChatRead.user_id == user.id,
                                ChatRead.room_id == room_uuid,
                            )
                        )).scalar_one_or_none()
                        if read_record:
                            read_record.last_read_message_id = uuid.UUID(message_id)
                            read_record.read_at = datetime.now(timezone.utc)
                        else:
                            db.add(ChatRead(
                                user_id=user.id,
                                room_id=room_uuid,
                                last_read_message_id=uuid.UUID(message_id),
                            ))
                        await db.commit()

                    await manager.broadcast(room_id, {
                        "type": "read_receipt",
                        "user_id": user_id_str,
                        "user_name": user.name,
                        "message_id": message_id,
                    }, exclude_user=user_id_str)

    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id_str)
        await manager.broadcast(room_id, {
            "type": "presence",
            "user_id": user_id_str,
            "user_name": user.name,
            "status": "offline",
            "online_users": manager.get_online_users(room_id),
        })
    except Exception:
        manager.disconnect(room_id, user_id_str)
