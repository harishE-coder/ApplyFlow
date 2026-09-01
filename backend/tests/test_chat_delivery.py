"""
Comprehensive test suite for chat real-time delivery lifecycle, presence, and unread counts.
"""

import uuid
from datetime import datetime, timezone

import pytest
from app.core.cache import cache
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.modules.chat import service
from app.modules.chat.models import ChatMessage, ChatRead, ChatRoom
from app.modules.chat.schemas import SendMessageRequest
from app.modules.chat.websocket import manager
from app.modules.clients.models import Client, EmployeeClient
from app.modules.users.models import User
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_state():
    cache.clear()
    manager.room_connections.clear()
    manager.user_connections.clear()
    manager.user_info.clear()
    yield
    cache.clear()
    manager.room_connections.clear()
    manager.user_connections.clear()
    manager.user_info.clear()


@pytest.fixture
async def test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
async def setup_env(test_db):
    client = Client(id=uuid.uuid4(), company_name="Delivery Corp", contact_person="HR", email="hr@delivery.io", is_active=True)
    test_db.add(client)

    room = ChatRoom(id=uuid.uuid4(), client_id=client.id, status="active")
    test_db.add(room)

    sender = User(id=uuid.uuid4(), name="Sender Employee", email="sender@flow.io", password_hash="hash123", role="employee", is_active=True, status="active")
    recipient = User(id=uuid.uuid4(), name="Recipient Client", email="client@delivery.io", password_hash="hash123", role="client", client_id=client.id, is_active=True, status="active")
    test_db.add_all([sender, recipient])

    test_db.add(EmployeeClient(employee_id=sender.id, client_id=client.id, active=True))
    await test_db.commit()

    return {"client": client, "room": room, "sender": sender, "recipient": recipient}


@pytest.mark.asyncio
async def test_message_delivery_offline_vs_online(test_db, setup_env):
    sender = setup_env["sender"]
    recipient = setup_env["recipient"]
    room = setup_env["room"]

    # 1. Recipient is offline -> initial status should be "sent"
    msg1 = await service.send_message(test_db, room.id, sender, "Hello offline recipient!")
    assert msg1.status == "sent"

    # 2. Simulate recipient connects (online)
    manager.user_connections[str(recipient.id)] = {"dummy_ws": str(room.id)}

    # 3. New message sent while recipient is online -> status should be "delivered"
    msg2 = await service.send_message(test_db, room.id, sender, "Hello online recipient!")
    assert msg2.status == "delivered"


@pytest.mark.asyncio
async def test_get_messages_status_lifecycle(test_db, setup_env):
    sender = setup_env["sender"]
    recipient = setup_env["recipient"]
    room = setup_env["room"]

    # Send message when recipient offline
    msg = await service.send_message(test_db, room.id, sender, "Test status lifecycle")
    await test_db.commit()

    # Recipient is offline -> get_messages returns "sent" for sender
    msgs_offline = await service.get_messages(test_db, room.id, sender)
    assert msgs_offline.items[-1].status == "sent"

    # Recipient connects
    manager.room_connections[str(room.id)] = {str(recipient.id): {}}
    msgs_online = await service.get_messages(test_db, room.id, sender)
    assert msgs_online.items[-1].status == "delivered"

    # Recipient marks message as read
    await service.mark_read(test_db, room.id, recipient, msg.id)
    await test_db.commit()

    msgs_read = await service.get_messages(test_db, room.id, sender)
    assert msgs_read.items[-1].status == "read"


@pytest.mark.asyncio
async def test_unread_count_schema(test_db, setup_env):
    sender = setup_env["sender"]
    recipient = setup_env["recipient"]
    room = setup_env["room"]

    # Sender sends 2 messages
    await service.send_message(test_db, room.id, sender, "Msg 1")
    await service.send_message(test_db, room.id, sender, "Msg 2")
    await test_db.commit()

    # Total unread for recipient
    res = await service.get_total_unread(test_db, recipient)
    assert res.total_unread == 2
    assert res.unread_count == 2

    # Recipient marks read
    await service.mark_read(test_db, room.id, recipient)
    await test_db.commit()

    res_after = await service.get_total_unread(test_db, recipient)
    assert res_after.total_unread == 0
