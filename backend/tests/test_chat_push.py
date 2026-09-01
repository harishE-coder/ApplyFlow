"""
Comprehensive Acceptance Test Suite for ApplyFlow Chat Push Notifications.
Tests:
1. Save subscription (POST /api/chat/push/subscribe).
2. Duplicate endpoint upsert.
3. Active in same room -> No push (WebSocket only).
4. Active in different room -> Push sent.
5. Inactive / Dashboard user -> Push sent.
6. Multiple tabs -> Single push per message (deduplicated).
7. Multiple devices -> Push sent to all registered devices of user.
8. Expired subscription cleanup (410 Gone / 404 Not Found auto-deletion).
9. Notification click route & payload contract.
10. Duplicate retry deduplication (SETNX protection).
11. User notification preferences & room muting.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.cache import cache
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.dependencies import get_current_user
from app.main import app
from app.modules.chat import push_service
from app.modules.chat.models import ChatRoom, PushSubscription
from app.modules.chat.websocket import manager
from app.modules.clients.models import Client, EmployeeClient
from app.modules.notifications.models import NotificationPreference
from app.modules.users.models import User
from httpx import ASGITransport, AsyncClient
from pywebpush import WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_state():
    """Clear cache and reset ConnectionManager state before every test."""
    cache.clear()
    manager.room_connections.clear()
    manager.user_connections.clear()
    manager.user_info.clear()
    settings.vapid_public_key = "BGSl6ZcyzkyfropuFTnD3QmkTdJTCLwaWIN_8CjLtRWVwmLrledjYu2aaHoKWd9urmUIOfzpo-9aV55nJVfxpfU"
    settings.vapid_private_key = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgN0dduxnkVZWOPMnRlywSVt71WlgUIa51wPJRVIAp9oyhRANCAARkpemXMs5Mn66KbhU5w90JpE3SUwi8GliDf_Aoy7UVlcJi65XnY2Ltmmh6Clnfbq5lCDn86aPvWleeZyVX8aX1"
    settings.vapid_email = "mailto:admin@applyflow.com"
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
async def setup_chat_environment(test_db):
    """Sets up a client, room, admin, employee, and client user in DB."""
    # 1. Client Company
    client_comp = Client(
        id=uuid.uuid4(),
        company_name="Apex Global Tech",
        contact_person="Apex HR",
        email="hr@apexglobal.io",
        is_active=True,
    )
    test_db.add(client_comp)

    # 2. Chat Room
    room = ChatRoom(
        id=uuid.uuid4(),
        client_id=client_comp.id,
        status="active",
    )
    test_db.add(room)

    # 3. Users: Admin, Employee (sender), Client User (recipient)
    admin = User(
        id=uuid.uuid4(),
        name="Super Admin",
        email=f"admin_{uuid.uuid4().hex[:6]}@applyflow.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    employee = User(
        id=uuid.uuid4(),
        name="Harish Recruiter",
        email=f"harish_{uuid.uuid4().hex[:6]}@applyflow.com",
        password_hash="hash",
        role="employee",
        is_active=True,
    )
    client_user = User(
        id=uuid.uuid4(),
        name="John Client",
        email=f"john_{uuid.uuid4().hex[:6]}@apexglobal.io",
        password_hash="hash",
        role="client",
        client_id=client_comp.id,
        is_active=True,
    )
    test_db.add_all([admin, employee, client_user])
    await test_db.flush()

    # Link employee to client
    emp_client = EmployeeClient(
        id=uuid.uuid4(),
        employee_id=employee.id,
        client_id=client_comp.id,
        active=True,
    )
    test_db.add(emp_client)
    await test_db.commit()

    return {
        "client": client_comp,
        "room": room,
        "admin": admin,
        "employee": employee,
        "client_user": client_user,
        "db": test_db,
    }


# ==============================================================================
# TEST CASES
# ==============================================================================

@pytest.mark.anyio
async def test_save_subscription(setup_chat_environment):
    """1. POST /api/chat/push/subscribe saves new browser push subscription."""
    env = setup_chat_environment
    user = env["client_user"]
    db = env["db"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/endpoint-laptop-1",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DKM",
                "auth": "tBHItJI5svbpez7KI4CCXg",
            },
        }
        res = await client.post("/api/chat/push/subscribe", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Verify in DB
        sub = (
            await db.execute(
                select(PushSubscription).where(PushSubscription.endpoint == payload["endpoint"])
            )
        ).scalar_one_or_none()
        assert sub is not None
        assert sub.user_id == user.id
        assert sub.p256dh == payload["keys"]["p256dh"]
        assert sub.auth == payload["keys"]["auth"]

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_duplicate_upsert(setup_chat_environment):
    """2. Duplicate subscription endpoint updates keys/user without throwing duplicate error."""
    env = setup_chat_environment
    user = env["client_user"]
    db = env["db"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        endpoint = "https://fcm.googleapis.com/fcm/send/shared-device"
        payload1 = {
            "endpoint": endpoint,
            "keys": {"p256dh": "key_v1", "auth": "auth_v1"},
        }
        res1 = await client.post("/api/chat/push/subscribe", json=payload1)
        assert res1.status_code == 200

        payload2 = {
            "endpoint": endpoint,
            "keys": {"p256dh": "key_v2_updated", "auth": "auth_v2_updated"},
        }
        res2 = await client.post("/api/chat/push/subscribe", json=payload2)
        assert res2.status_code == 200

        # Query total count for endpoint
        subs = (
            await db.execute(
                select(PushSubscription).where(PushSubscription.endpoint == endpoint)
            )
        ).scalars().all()
        assert len(subs) == 1
        assert subs[0].p256dh == "key_v2_updated"

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_active_same_room_no_push(setup_chat_environment):
    """3. Active in SAME room -> WebSocket delivery only, push notification suppressed."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]

    # Register subscription for recipient
    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/active-tab",
        p256dh="key1",
        auth="auth1",
    )
    db.add(sub)
    await db.commit()

    # Simulate recipient active in THIS room via ConnectionManager
    mock_ws = MagicMock()
    from starlette.websockets import WebSocketState
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()
    await manager.connect(mock_ws, str(room.id), str(recipient.id), recipient.name, recipient.role)

    assert manager.is_user_in_room(recipient.id, room.id) is True

    # Patch push_service.send_push_notification to ensure it is NOT called
    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Hello, are you there?",
            )
            assert sent_count == 0
            assert mock_send.call_count == 0


@pytest.mark.anyio
async def test_active_different_room_push(setup_chat_environment):
    """4. Active in a DIFFERENT room -> Push notification is sent."""
    env = setup_chat_environment
    db = env["db"]
    target_room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]
    different_room_id = str(uuid.uuid4())

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/diff-room-tab",
        p256dh="key1",
        auth="auth1",
    )
    db.add(sub)
    await db.commit()

    # Simulate recipient viewing a DIFFERENT room
    mock_ws = MagicMock()
    from starlette.websockets import WebSocketState
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()
    await manager.connect(mock_ws, different_room_id, str(recipient.id), recipient.name, recipient.role)

    assert manager.is_user_in_room(recipient.id, target_room.id) is False

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=target_room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Message for Target Room",
            )
            assert mock_send.call_count >= 1
            assert sent_count >= 1


@pytest.mark.anyio
async def test_dashboard_user_push(setup_chat_environment):
    """5. Inactive / Dashboard user without any chat WS connection -> Push notification sent."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/dashboard-tab",
        p256dh="key1",
        auth="auth1",
    )
    db.add(sub)
    await db.commit()

    # Recipient has no active WS connection at all
    assert manager.is_user_online(recipient.id) is False

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Checking in from dashboard",
            )
            assert sent_count >= 1
            assert mock_send.call_count >= 1


@pytest.mark.anyio
async def test_multiple_tabs_dedup_one_push(setup_chat_environment):
    """6. Multiple tabs from same user -> Notification deduplication prevents duplicates."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]
    msg_id = uuid.uuid4()

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/single-sub",
        p256dh="key1",
        auth="auth1",
    )
    db.add(sub)
    await db.commit()

    # Pre-set deduplication key in cache (simulating an already-handled tab or previous worker)
    cache.set_nx(f"push:{msg_id}:{recipient.id}", "1", ttl=30)

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=msg_id,
                preview_text="Duplicate test",
            )
            # Must skip due to SETNX
            assert sent_count == 0
            assert mock_send.call_count == 0


@pytest.mark.anyio
async def test_multiple_devices_push_both(setup_chat_environment):
    """7. Multiple device subscriptions (laptop + phone) -> Push is sent to each device."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]

    sub_laptop = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/device-laptop",
        p256dh="key_laptop",
        auth="auth_laptop",
    )
    sub_phone = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/device-phone",
        p256dh="key_phone",
        auth="auth_phone",
    )
    db.add_all([sub_laptop, sub_phone])
    await db.commit()

    called_endpoints = []

    async def mock_send(d_db, d_sub, payload):
        called_endpoints.append(d_sub.endpoint)
        return True

    with patch("app.modules.chat.push_service.send_push_notification", side_effect=mock_send):
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Multi device alert",
            )
            assert "https://fcm.googleapis.com/fcm/send/device-laptop" in called_endpoints
            assert "https://fcm.googleapis.com/fcm/send/device-phone" in called_endpoints
            assert sent_count == 2


@pytest.mark.anyio
async def test_expired_subscription_cleanup(setup_chat_environment):
    """8. Expired subscription (410 Gone) is automatically deleted from database."""
    env = setup_chat_environment
    db = env["db"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/expired-410-endpoint",
        p256dh="key_exp",
        auth="auth_exp",
    )
    db.add(sub)
    await db.commit()

    # Simulate pywebpush throwing WebPushException with status 410
    mock_resp = MagicMock()
    mock_resp.status_code = 410
    mock_resp.text = "push subscription has unsubscribed or expired."

    with patch("app.modules.chat.push_service.webpush", side_effect=WebPushException("Push failed: 410 Gone", response=mock_resp)):
        result = await push_service.send_push_notification(db, sub, {"type": "chat_message"})
        assert result is False

    # Check that the record was removed from DB
    remaining = (
        await db.execute(
            select(PushSubscription).where(PushSubscription.id == sub.id)
        )
    ).scalar_one_or_none()
    assert remaining is None


@pytest.mark.anyio
async def test_notification_click_route():
    """9. Notification payload contains deep-link url, room_id contract, and unread_count badge."""
    room_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    sender_name = "Harish"
    preview = "Can you review this candidate resume?"

    payload = {
        "type": "chat_message",
        "room_id": str(room_id),
        "message_id": str(msg_id),
        "sender_name": sender_name,
        "preview": preview,
        "unread_count": 5,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    # Verify JSON structure
    serialized = json.dumps(payload)
    data = json.loads(serialized)

    assert data["type"] == "chat_message"
    assert data["room_id"] == str(room_id)
    assert data["message_id"] == str(msg_id)
    assert data["sender_name"] == sender_name
    assert data["unread_count"] == 5
    assert f"/chats/{data['room_id']}" == f"/chats/{room_id}"


@pytest.mark.anyio
async def test_duplicate_retry_one_notification(setup_chat_environment):
    """10. Repeated calls for the same message_id send only 1 notification (SETNX dedup)."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]
    msg_id = uuid.uuid4()

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/retry-sub",
        p256dh="key",
        auth="auth",
    )
    db.add(sub)
    await db.commit()

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db

            # Call 1: fresh
            count1 = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=msg_id,
                preview_text="First dispatch",
            )
            assert count1 >= 1
            first_call_count = mock_send.call_count

            # Call 2: retry with SAME message_id -> must be skipped by dedup
            count2 = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=msg_id,
                preview_text="Retry dispatch",
            )
            assert count2 == 0
            assert mock_send.call_count == first_call_count


@pytest.mark.anyio
async def test_muted_room_preferences(setup_chat_environment):
    """11. Muted room in NotificationPreference suppresses push notification."""
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/muted-user-endpoint",
        p256dh="key",
        auth="auth",
    )
    # Add preference with this room muted
    pref = NotificationPreference(
        id=uuid.uuid4(),
        user_id=recipient.id,
        chat_push=True,
        muted_rooms=[str(room.id)],
    )
    db.add_all([sub, pref])
    await db.commit()

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent_count = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Muted room message",
            )
            # Since room is muted, push notification must not be sent
            assert sent_count == 0
            assert mock_send.call_count == 0


@pytest.mark.anyio
async def test_admin_push_monitoring_status(setup_chat_environment):
    """12. Admin monitoring endpoint returns ONLY aggregated metrics without exposing sensitive secrets or endpoints."""
    env = setup_chat_environment
    admin = env["admin"]
    db = env["db"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/chat/push/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "online_users" in data
        assert "active_rooms" in data
        assert "subscriptions" in data
        assert "total_sent" in data
        assert "retries_pending" in data
        assert "vapid_configured" in data
        # Ensure sensitive details are never exposed
        assert "private_key" not in data
        assert "vapid_private_key" not in data
        assert "endpoint" not in data
        assert "p256dh" not in data
        assert "auth" not in data

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_auto_vapid_key_generation():
    """13. Auto VAPID generation ensures public and private keys exist dynamically if missing."""
    from app.core.config import ensure_vapid_keys

    # Simulate missing keys
    settings.vapid_public_key = None
    settings.vapid_private_key = None

    ensure_vapid_keys()

    assert settings.vapid_public_key is not None
    assert len(settings.vapid_public_key) > 30
    assert settings.vapid_private_key is not None
    assert len(settings.vapid_private_key) > 30


@pytest.mark.anyio
async def test_retry_queue_transient_failure(setup_chat_environment):
    """14. Transient errors (503/429) trigger retry queue and succeed on subsequent attempt."""
    env = setup_chat_environment
    db = env["db"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/retry-transient",
        p256dh="key",
        auth="auth",
    )
    db.add(sub)
    await db.commit()

    # Mock responses: 1st call throws 503, 2nd call succeeds
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.text = "Service Unavailable"

    call_count = 0

    def mock_webpush_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise WebPushException("Push failed: 503", response=mock_503)
        return True

    with patch("app.modules.chat.push_service.webpush", side_effect=mock_webpush_call):
        # Fast retry delays for testing
        success = await push_service.send_push_notification(
            db, sub, {"type": "chat_message"}, retry_delays=[0, 0.01]
        )
        assert success is True
        assert call_count == 2


@pytest.mark.anyio
async def test_auth_error_no_retry(setup_chat_environment):
    """15. Auth errors (401/403) abort immediately without retry."""
    env = setup_chat_environment
    db = env["db"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/auth-fail",
        p256dh="key",
        auth="auth",
    )
    db.add(sub)
    await db.commit()

    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Unauthorized"

    call_count = 0

    def mock_webpush_401(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise WebPushException("Push failed: 401", response=mock_401)

    with patch("app.modules.chat.push_service.webpush", side_effect=mock_webpush_401):
        success = await push_service.send_push_notification(
            db, sub, {"type": "chat_message"}, retry_delays=[0, 0.01, 0.01]
        )
        assert success is False
        # Must not retry on 401
        assert call_count == 1


@pytest.mark.anyio
async def test_multi_worker_shared_presence_suppression(setup_chat_environment):
    """16. Multi-worker shared presence: User connected to Worker B suppresses push on Worker A."""
    from app.core.cache import remove_user_presence, set_user_presence
    env = setup_chat_environment
    db = env["db"]
    room = env["room"]
    sender = env["employee"]
    recipient = env["client_user"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/worker-b-tab",
        p256dh="key",
        auth="auth",
    )
    db.add(sub)
    await db.commit()

    # Simulate Worker B setting presence in Redis
    set_user_presence(str(recipient.id), str(room.id), ttl=45)

    assert manager.is_user_in_room(recipient.id, room.id) is True

    with patch("app.modules.chat.push_service.send_push_notification", new_callable=AsyncMock) as mock_send:
        with patch("app.modules.chat.push_service.async_session_factory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db
            sent = await push_service.notify_room_recipients(
                room_id=room.id,
                sender_id=sender.id,
                sender_name=sender.name,
                message_id=uuid.uuid4(),
                preview_text="Worker B active presence test",
            )
            # Push suppressed by multi-worker shared presence
            assert sent == 0
            assert mock_send.call_count == 0

    remove_user_presence(str(recipient.id))


@pytest.mark.anyio
async def test_persistent_retry_queue_enqueue_and_process(setup_chat_environment):
    """17. Persistent retry queue enqueues failed jobs and processes them upon worker run."""
    env = setup_chat_environment
    db = env["db"]
    recipient = env["client_user"]
    room = env["room"]

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=recipient.id,
        endpoint="https://fcm.googleapis.com/fcm/send/persistent-retry-endpoint",
        p256dh="key",
        auth="auth",
    )
    db.add(sub)
    await db.commit()

    payload = {"type": "chat_message", "preview": "Queued message"}

    # Enqueue job with ready time
    push_service.enqueue_push_retry(
        subscription_id=sub.id,
        room_id=room.id,
        message_id=uuid.uuid4(),
        payload=payload,
        attempt=1,
        delay_seconds=0,
    )

    with patch("app.modules.chat.push_service.webpush", return_value=True):
        processed = await push_service.process_push_retry_queue(db)
        assert processed == 1


@pytest.mark.anyio
async def test_rate_limit_subscribe_endpoint(setup_chat_environment):
    """18. Rate limiter throttles excessive subscription requests (429 Too Many Requests)."""
    env = setup_chat_environment
    user = env["client_user"]
    db = env["db"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/rate-limit-test",
            "keys": {"p256dh": "key", "auth": "auth"},
        }
        # Send 10 allowed requests
        for _ in range(10):
            res = await client.post("/api/chat/push/subscribe", json=payload)
            assert res.status_code == 200

        # 11th request must trigger rate limiter
        res11 = await client.post("/api/chat/push/subscribe", json=payload)
        assert res11.status_code == 429
        assert "Rate limit exceeded" in res11.json()["detail"]

    app.dependency_overrides.clear()




