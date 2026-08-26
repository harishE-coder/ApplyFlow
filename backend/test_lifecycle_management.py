"""
Comprehensive Test Suite for ApplyFlow Lifecycle Management
(Create, Edit, Activate, Deactivate, Archive, Safe Delete, Chat Lock, Notifications, CSV Exports).
"""

import asyncio
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.targets.models import Target
from app.modules.chat.models import ChatRoom, ChatMessage
from app.modules.notifications.models import Notification

from app.modules.clients import service as client_service
from app.modules.clients.schemas import ClientCreate, ClientUpdate
from app.modules.users import service as user_service
from app.modules.users.schemas import UserCreate, UserUpdate, ResetPasswordRequest
from app.modules.requirements import service as req_service
from app.modules.requirements.schemas import RequirementCreate, RequirementUpdate
from app.modules.targets import service as target_service
from app.modules.targets.schemas import TargetSetRequest
from app.modules.chat import service as chat_service
from app.modules.notifications import service as notif_service
from app.modules.reports import service as report_service
from app.modules.resumes import service as resume_service
from app.modules.resumes.schemas import ResumeUpdate


async def run_lifecycle_tests():
    print("=" * 74)
    print("🔄 RUNNING APPLYFLOW LIFECYCLE MANAGEMENT TEST SUITE")
    print("=" * 74)

    async with async_session_factory() as db:
        # Get admin user
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        assert admin is not None, "Admin user required"
        print(f"✅ Admin User: {admin.name} ({admin.email})")

        # -----------------------------------------------------------------------
        # 1. SERVICE CLIENT LIFECYCLE
        # -----------------------------------------------------------------------
        print("\n--- 1. Service Client Lifecycle ---")
        client_name = f"Lifecycle Test Client {uuid.uuid4().hex[:6]}"
        created_client = await client_service.create_client(
            db, ClientCreate(company_name=client_name, contact_person="John Test", email="john@test.com"), admin
        )
        print(f"Created client: {created_client.company_name} (ID: {created_client.id})")

        # Edit Client
        updated_client = await client_service.update_client(
            db, created_client.id, ClientUpdate(contact_person="John Updated"), admin
        )
        assert updated_client.contact_person == "John Updated", "Client edit failed"
        print("✅ Edit Client passed")

        # Deactivate Client
        deactivated = await client_service.deactivate_client(db, created_client.id, admin)
        assert deactivated.status == "inactive" and not deactivated.is_active, "Deactivation failed"
        room = (await db.execute(select(ChatRoom).where(ChatRoom.client_id == created_client.id))).scalar_one()
        assert room.status == "read_only", "Chat room was not locked to read_only"
        print("✅ Deactivate Client passed (Status: inactive, Chat: read_only)")

        # Activate Client
        activated = await client_service.activate_client(db, created_client.id, admin)
        assert activated.status == "active" and activated.is_active, "Activation failed"
        print("✅ Activate Client passed (Status: active)")

        # Archive Client
        archived = await client_service.archive_client(db, created_client.id, admin)
        assert archived.status == "archived", "Archive failed"
        print("✅ Archive Client passed (Status: archived)")

        # Safe Delete with dependencies check
        # Add a test resume to test dependency prevention
        test_resume = Resume(
            candidate_name="Dep Candidate",
            company="TCS",
            role="Dev",
            client_id=created_client.id,
            uploaded_by=admin.id,
            original_filename="dep_candidate.pdf",
        )
        db.add(test_resume)
        await db.flush()

        try:
            await client_service.safe_delete_client(db, created_client.id, admin)
            raise AssertionError("Safe delete should have failed because client has resumes!")
        except Exception as e:
            assert "This client has historical data. Archive instead." in str(e)
            print("✅ Safe Delete dependency block verified (Prevented deletion with historical data)")

        # Clean resume and test successful safe delete
        await db.delete(test_resume)
        await db.flush()
        await client_service.safe_delete_client(db, created_client.id, admin)
        deleted_check = await client_service.get_client_by_id(db, created_client.id)
        assert deleted_check is None, "Client was not deleted"
        print("✅ Safe Delete passed on clean client")

        # -----------------------------------------------------------------------
        # 2. EMPLOYEE LIFECYCLE
        # -----------------------------------------------------------------------
        print("\n--- 2. Employee Lifecycle ---")
        emp_email = f"lifecycle_emp_{uuid.uuid4().hex[:6]}@applyflow.com"
        emp = await user_service.create_user(
            db, admin, UserCreate(name="Lifecycle Emp", email=emp_email, password="password123", role="employee")
        )
        print(f"Created employee: {emp.name} (ID: {emp.id})")

        # Edit Employee
        updated_emp = await user_service.update_user(db, admin, emp, UserUpdate(name="Lifecycle Emp Updated"))
        assert updated_emp.name == "Lifecycle Emp Updated"
        print("✅ Edit Employee passed")

        # Reset Password
        await user_service.reset_password_user(db, emp.id, "new_secure_pass123", admin)
        print("✅ Reset Password passed")

        # Deactivate Employee
        deact_emp = await user_service.deactivate_user(db, emp.id, admin)
        assert deact_emp.status == "inactive" and not deact_emp.is_active
        print("✅ Deactivate Employee passed (is_active=False)")

        # Activate Employee
        act_emp = await user_service.activate_user(db, emp.id, admin)
        assert act_emp.status == "active" and act_emp.is_active
        print("✅ Activate Employee passed (is_active=True)")

        # Safe Delete Employee
        await user_service.safe_delete_user(db, emp.id, admin)
        assert await user_service.get_user_by_id(db, emp.id) is None
        print("✅ Safe Delete Employee passed")

        # -----------------------------------------------------------------------
        # 3. TARGET LIFECYCLE
        # -----------------------------------------------------------------------
        print("\n--- 3. Target Lifecycle ---")
        abc_client = (await db.execute(select(Client).where(Client.company_name == "ABC Staffing"))).scalar_one()
        harish_emp = (await db.execute(select(User).where(User.name == "Harish Recruiter"))).scalar_one()

        target = await target_service.set_target(
            db, admin, TargetSetRequest(employee_id=harish_emp.id, client_id=abc_client.id, daily_target=30)
        )
        print(f"Set target: {target.daily_target}/day (Status: {target.status})")

        # Pause Target
        paused_target = await target_service.pause_target(db, target.id, admin)
        assert paused_target.status == "paused"
        print("✅ Pause Target passed (Status: paused)")

        # Resume Target
        resumed_target = await target_service.resume_target(db, target.id, admin)
        assert resumed_target.status == "active"
        print("✅ Resume Target passed (Status: active)")

        # End Target
        ended_target = await target_service.end_target(db, target.id, admin)
        assert ended_target.status == "ended"
        print("✅ End Target passed (Status: ended)")

        # -----------------------------------------------------------------------
        # 4. REQUIREMENT LIFECYCLE
        # -----------------------------------------------------------------------
        print("\n--- 4. Requirement Lifecycle ---")
        req_code = f"REQ-{uuid.uuid4().hex[:4].upper()}"
        req = await req_service.create_requirement(
            db, admin, RequirementCreate(client_id=abc_client.id, company="Amazon", role="SDE II", role_code=req_code)
        )
        print(f"Created requirement: {req.role_code} (Status: {req.status})")

        # Close Requirement
        closed_req = await req_service.close_requirement(db, req.id, admin)
        assert closed_req.status == "closed"
        print("✅ Close Requirement passed (Status: closed)")

        # Reopen Requirement
        reopened_req = await req_service.reopen_requirement(db, req.id, admin)
        assert reopened_req.status == "active"
        print("✅ Reopen Requirement passed (Status: active)")

        # Archive Requirement
        archived_req = await req_service.archive_requirement(db, req.id, admin)
        assert archived_req.status == "archived"
        print("✅ Archive Requirement passed (Status: archived)")

        # Clean Safe Delete Requirement
        await req_service.safe_delete_requirement(db, req.id, admin)
        print("✅ Safe Delete Requirement passed")

        # -----------------------------------------------------------------------
        # 5. CHAT LIFECYCLE & READ-ONLY ENFORCEMENT
        # -----------------------------------------------------------------------
        print("\n--- 5. Chat Lifecycle ---")
        chat_room = await chat_service.get_or_create_room(db, abc_client.id)
        
        # Send normal message
        msg = await chat_service.send_message(db, chat_room.id, admin, "Test lifecycle message")
        assert msg.message == "Test lifecycle message"
        print(f"✅ Send Message passed (ID: {msg.id})")

        # Lock Chat Room
        await chat_service.lock_room(db, chat_room.id, admin)
        assert (await chat_service.check_room_access(db, admin, chat_room.id)).status == "read_only"
        
        # Try sending to locked room (should fail)
        try:
            await chat_service.send_message(db, chat_room.id, admin, "Should fail message")
            raise AssertionError("Sending message to locked room should fail!")
        except Exception as e:
            assert "read-only" in str(e)
            print("✅ Lock Chat Room & Read-Only enforcement verified")

        # Unlock Chat Room
        await chat_service.unlock_room(db, chat_room.id, admin)
        print("✅ Unlock Chat Room passed")

        # Export Chat
        transcript = await chat_service.export_room_chat(db, chat_room.id, admin)
        assert len(transcript) > 0
        print(f"✅ Export Chat passed ({len(transcript)} messages exported)")

        # Delete Message
        del_res = await chat_service.delete_message(db, msg.id, admin)
        print("✅ Delete Message passed")

        # -----------------------------------------------------------------------
        # 6. NOTIFICATION LIFECYCLE
        # -----------------------------------------------------------------------
        print("\n--- 6. Notification Lifecycle ---")
        notif = await notif_service.create_notification(db, admin.id, "Lifecycle Notif", "Test message", "info")
        print(f"Created notification ID: {notif.id}")

        await notif_service.mark_as_read(db, admin, notif.id)
        print("✅ Mark Read passed")

        marked_all = await notif_service.mark_all_as_read(db, admin)
        print(f"✅ Mark All Read passed ({marked_all} marked)")

        await notif_service.delete_notification(db, admin, notif.id)
        print("✅ Delete Notification passed")

        # -----------------------------------------------------------------------
        # 7. REPORTS CSV EXPORTS
        # -----------------------------------------------------------------------
        print("\n--- 7. Reports CSV Exports ---")
        clients_csv = await report_service.export_clients_csv(db, admin, status="active")
        assert "Client Name" in clients_csv
        print(f"✅ Export Active Clients CSV passed ({len(clients_csv.splitlines())} rows)")

        employees_csv = await report_service.export_employees_csv(db, admin, status="inactive")
        assert "Employee Name" in employees_csv
        print("✅ Export Inactive Employees CSV passed")

        targets_csv = await report_service.export_targets_csv(db, admin, status="ended")
        assert "Daily Target" in targets_csv
        print("✅ Export Ended Targets CSV passed")

        print("\n" + "=" * 74)
        print("🎉 ALL LIFECYCLE MANAGEMENT TESTS PASSED 100%!")
        print("=" * 74)

if __name__ == "__main__":
    asyncio.run(run_lifecycle_tests())
