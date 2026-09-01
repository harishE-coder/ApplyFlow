"""
Chat WebSocket endpoint for real-time messaging.
Handles message broadcasting, typing indicators, read receipts, and presence.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from starlette.websockets import WebSocketState

from app.core.cache import (
    get_user_presence,
    is_user_in_room_shared,
    remove_user_presence,
    set_user_presence,
)
from app.core.database import async_session_factory
from app.core.security import decode_token
from app.modules.chat.models import ChatMessage, ChatRead, ChatRoom
from app.modules.clients.models import EmployeeClient
from app.modules.users.models import User

router = APIRouter()


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections per room and per user with room-level tracking,
    cross-room live delivery broadcasts, and multi-worker Redis shared presence support.
    """

    def __init__(self):
        # room_id -> { user_id -> set of WebSockets }
        self.room_connections: dict[str, dict[str, set[WebSocket]]] = {}
        # user_id -> { WebSocket: active_room_id }
        self.user_connections: dict[str, dict[WebSocket, str]] = {}
        # user_id -> user info
        self.user_info: dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str, user_role: str):
        if websocket.client_state != WebSocketState.CONNECTED:
            await websocket.accept()

        rid = str(room_id)
        uid = str(user_id)

        if rid not in self.room_connections:
            self.room_connections[rid] = {}
        if uid not in self.room_connections[rid]:
            self.room_connections[rid][uid] = set()

        self.room_connections[rid][uid].add(websocket)

        if uid not in self.user_connections:
            self.user_connections[uid] = {}
        self.user_connections[uid][websocket] = rid

        self.user_info[uid] = {"name": user_name, "role": user_role}

        # Multi-worker shared presence sync
        set_user_presence(uid, rid, ttl=45)

        # Broadcast presence
        await self.broadcast(rid, {
            "type": "presence",
            "user_id": uid,
            "user_name": user_name,
            "status": "online",
            "online_users": self.get_online_users(rid),
        }, exclude_user=None)

        # Trigger delivery update for sender messages in this room
        await self.broadcast(rid, {
            "type": "message_status",
            "status": "delivered",
            "room_id": rid,
            "delivered_to": uid,
        }, exclude_user=uid)

    def disconnect(self, websocket: WebSocket, room_id: str, user_id: str):
        rid = str(room_id)
        uid = str(user_id)

        if rid in self.room_connections and uid in self.room_connections[rid]:
            self.room_connections[rid][uid].discard(websocket)
            if not self.room_connections[rid][uid]:
                del self.room_connections[rid][uid]
            if not self.room_connections[rid]:
                del self.room_connections[rid]

        if uid in self.user_connections:
            self.user_connections[uid].pop(websocket, None)
            if not self.user_connections[uid]:
                del self.user_connections[uid]

        # Multi-worker shared presence cleanup
        remove_user_presence(uid, rid)

    def is_user_in_room(self, user_id: str | uuid.UUID, room_id: str | uuid.UUID) -> bool:
        """Returns True if the user has an active WebSocket in this room on THIS worker or ANY worker."""
        rid = str(room_id)
        uid = str(user_id)
        if bool(self.room_connections.get(rid, {}).get(uid)):
            return True
        return is_user_in_room_shared(uid, rid)

    def is_user_online(self, user_id: str | uuid.UUID) -> bool:
        """Returns True if the user has ANY active WebSocket connection on THIS worker or ANY worker."""
        uid = str(user_id)
        if bool(self.user_connections.get(uid)):
            return True
        return bool(get_user_presence(uid))

    def get_online_users(self, room_id: str | uuid.UUID) -> list[str]:
        """Returns list of unique user IDs active in this room."""
        rid = str(room_id)
        return list(self.room_connections.get(rid, {}).keys())

    async def broadcast(self, room_id: str | uuid.UUID, message: dict, exclude_user: str | None = None):
        """Send message to all connected clients in a room."""
        rid = str(room_id)
        if rid not in self.room_connections:
            return

        dead = []
        exclude_uid = str(exclude_user) if exclude_user else None

        for uid, ws_set in list(self.room_connections[rid].items()):
            if uid == exclude_uid:
                continue
            for ws in list(ws_set):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((uid, ws))

        for uid, ws in dead:
            self.disconnect(ws, rid, uid)

    async def send_to_user(self, room_id: str | uuid.UUID, user_id: str | uuid.UUID, message: dict):
        """Send message to all active sockets of a specific user in a room."""
        rid = str(room_id)
        uid = str(user_id)
        if rid in self.room_connections and uid in self.room_connections[rid]:
            dead = []
            for ws in list(self.room_connections[rid][uid]):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, rid, uid)

    async def send_to_user_global(self, user_id: str | uuid.UUID, message: dict):
        """Send message to all active sockets of a user anywhere across the application."""
        uid = str(user_id)
        if uid in self.user_connections:
            dead = []
            for ws, rid in list(self.user_connections[uid].items()):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((ws, rid))
            for ws, rid in dead:
                self.disconnect(ws, rid, uid)

    async def broadcast_room_update(self, room_id: str | uuid.UUID, participant_ids: list[str | uuid.UUID], message: dict):
        """Broadcast room snippet / unread updates to all participants across all active pages."""
        for pid in participant_ids:
            await self.send_to_user_global(pid, message)


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
            select(User).where(User.id == uuid.UUID(user_id), User.is_active == True)
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
                    EmployeeClient.active == True,
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

    # Support global user connection identifier
    is_user_global_socket = room_id in ("global", "user")

    if not is_user_global_socket:
        try:
            room_uuid = uuid.UUID(room_id)
        except ValueError:
            await websocket.close(code=4002, reason="Invalid room ID")
            return

        if not await check_ws_room_access(user, room_uuid):
            await websocket.close(code=4003, reason="Access denied")
            return
    else:
        room_uuid = None

    user_id_str = str(user.id)
    await manager.connect(websocket, room_id, user_id_str, user.name, user.role)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message" and not is_user_global_socket:
                # Save message to DB
                text = data.get("text", "").strip()
                client_id = data.get("client_id")
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
                        read_record.last_read_at = datetime.now(timezone.utc)
                    else:
                        db.add(ChatRead(
                            user_id=user.id,
                            room_id=room_uuid,
                            last_read_message_id=msg.id,
                        ))

                    await db.commit()

                    # Determine initial delivery status: delivered if any other user is online/in room
                    online_users = manager.get_online_users(room_id)
                    has_recipients = any(uid != user_id_str for uid in online_users) or any(
                        manager.is_user_online(uid) for uid in manager.user_connections if uid != user_id_str
                    )
                    msg_status = "delivered" if has_recipients else "sent"

                    msg_payload = {
                        "id": str(msg.id),
                        "room_id": room_id,
                        "client_id": client_id,
                        "status": msg_status,
                        "sender": {
                            "id": user_id_str,
                            "name": user.name,
                            "role": user.role,
                        },
                        "message": text,
                        "attachment_type": None,
                        "attachment_reference": None,
                        "attachment_filename": None,
                        "created_at": msg.created_at.isoformat() if msg.created_at else datetime.now(timezone.utc).isoformat(),
                        "is_deleted": False,
                    }

                    # Broadcast to all in room
                    await manager.broadcast(room_id, {
                        "type": "new_message",
                        "message": msg_payload,
                    })

                    # Dispatch push notification to inactive room participants in background
                    from app.modules.chat.push_service import notify_room_recipients
                    asyncio.create_task(
                        notify_room_recipients(
                            room_id=room_uuid,
                            sender_id=user.id,
                            sender_name=user.name,
                            message_id=msg.id,
                            preview_text=text,
                            attachment_type=None,
                            created_at=msg.created_at,
                        )
                    )

            elif msg_type == "delivery_ack" and not is_user_global_socket:
                message_id = data.get("message_id")
                if message_id:
                    await manager.broadcast(room_id, {
                        "type": "message_status",
                        "message_id": str(message_id),
                        "status": "delivered",
                    })

            elif msg_type == "typing" and not is_user_global_socket:
                await manager.broadcast(room_id, {
                    "type": "typing",
                    "user_id": user_id_str,
                    "user_name": user.name,
                    "is_typing": data.get("is_typing", True),
                }, exclude_user=user_id_str)

            elif msg_type == "read" and not is_user_global_socket:
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
                            read_record.last_read_at = datetime.now(timezone.utc)
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

                    await manager.broadcast(room_id, {
                        "type": "message_status",
                        "message_id": message_id,
                        "status": "read",
                        "read_by": user_id_str,
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id, user_id_str)
        if not is_user_global_socket:
            await manager.broadcast(room_id, {
                "type": "presence",
                "user_id": user_id_str,
                "user_name": user.name,
                "status": "offline",
                "online_users": manager.get_online_users(room_id),
            })
    except Exception:
        manager.disconnect(websocket, room_id, user_id_str)


