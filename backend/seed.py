"""
ApplyFlow Production Database Initialization & Seed Script.
Initializes a clean, empty production database with the single Super Admin account in Neon PostgreSQL.
"""

import asyncio
from sqlalchemy import create_engine, delete, select
from app.core.config import settings
from app.core.database import async_session_factory, Base
from app.core.security import hash_password
from app.modules.users.models import User, SubAdminAssignment
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application, ApplicationEvent
from app.modules.targets.models import Target
from app.modules.activity_logs.models import ActivityLog
from app.modules.attendance.models import Attendance
from app.modules.notifications.models import Notification
from app.modules.chat.models import ChatRoom, ChatMessage, ChatRead


async def seed_database():
    print("🌱 Initializing clean production database schema in Neon PostgreSQL...", flush=True)

    async with async_session_factory() as db:
        # Clear all tables in correct FK order
        await db.execute(delete(ChatRead))
        await db.execute(delete(ChatMessage))
        await db.execute(delete(ChatRoom))
        await db.execute(delete(Notification))
        await db.execute(delete(Attendance))
        await db.execute(delete(ActivityLog))
        await db.execute(delete(Target))
        await db.execute(delete(ApplicationEvent))
        await db.execute(delete(Application))
        await db.execute(delete(Resume))
        await db.execute(delete(Requirement))
        await db.execute(delete(SubAdminAssignment))
        await db.execute(delete(EmployeeClient))
        await db.execute(delete(User))
        await db.execute(delete(Client))
        await db.flush()

        # Seed only the single production Super Admin account
        admin_email = (settings.admin_email or "Harishabblu123@gmail.com").lower()
        admin_pass = settings.admin_password or "Harish@2007"
        admin_name = settings.admin_name or "Harish Admin"

        admin_user = User(
            name=admin_name,
            email=admin_email,
            password_hash=hash_password(admin_pass),
            role="admin",
            is_active=True,
            status="active",
        )
        db.add(admin_user)
        await db.commit()

        print("=================================================================")
        print("✅ ApplyFlow Production Database Initialized Successfully!")
        print(f"👑 Super Admin Account: {admin_email} (Role: admin)")
        print("📁 All demo/testing data cleared. Clean database ready for production.")
        print("=================================================================")


if __name__ == "__main__":
    asyncio.run(seed_database())
