import uuid

import pytest
from app.core.database import async_session_factory
from app.modules.clients import service as client_service
from app.modules.clients.schemas import ClientCreate
from app.modules.users.models import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_client_creates_client_login_account():
    async with async_session_factory() as db:
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if admin is None:
            pytest.skip("No admin user exists in the current database")

        company_name = f"Client Login Test {uuid.uuid4().hex[:6]}"
        payload = ClientCreate(
            company_name=company_name,
            contact_person="Jane Client",
            email="jane.client@example.com",
            phone="+1-555-0101",
            password="ClientPass123!",
        )

        client = await client_service.create_client(db, payload, admin)

        created_user = (
            await db.execute(
                select(User).where(User.email == "jane.client@example.com", User.role == "client")
            )
        ).scalar_one_or_none()

        assert created_user is not None
        assert created_user.client_id == client.id
        assert created_user.role == "client"
