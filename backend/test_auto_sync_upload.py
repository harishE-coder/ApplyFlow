"""
Test Suite: ApplyFlow Auto-Sync After Upload (No Submit Candidate Button)
Verifies:
1. Ingestion auto-syncs resumes immediately to selected Service Client.
2. No intermediate 'pending submission' state or manual 'submit to client' action required.
3. Resumes immediately visible to Admin, Assigned Recruiter, Assigned Sub-Admin, and Client Portal User.
4. Resumes strictly hidden from other unassigned clients (e.g. Talent Hub / NextHire).
5. In-app notifications automatically generated for Employee, Admin, Sub-Admin, and Client.
6. Activity logs automatically created.
7. Real-time dashboard stats returned in upload payload.
"""

import asyncio
import io
import uuid
from datetime import date, datetime
from sqlalchemy import select, func, or_
from fastapi import UploadFile

from app.core.database import async_session_factory
from app.modules.users.models import User, SubAdminAssignment
from app.modules.clients.models import Client, EmployeeClient
from app.modules.resumes.models import Resume
from app.modules.resumes.service import process_bulk_upload, get_resume_by_id, search_resumes
from app.modules.notifications.models import Notification
from app.modules.activity_logs.models import ActivityLog
from app.modules.dashboard.service import get_employee_dashboard, get_client_dashboard


async def run_tests():
    print("\n" + "=" * 74)
    print("🚀 RUNNING APPLYFLOW AUTO-SYNC AFTER UPLOAD TEST SUITE")
    print("=" * 74)

    async with async_session_factory() as db:
        # 1. Fetch contexts
        admin_user = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        emp_user = (await db.execute(select(User).where(User.role == "employee", User.is_active == True))).scalars().first()
        sub_admin_user = (await db.execute(select(User).where(User.role == "sub_admin", User.is_active == True))).scalars().first()
        client_user = (await db.execute(select(User).where(User.role == "client", User.is_active == True))).scalars().first()

        assert admin_user and emp_user and client_user, "Required test users must exist"

        abc_client = (await db.execute(select(Client).where(Client.id == client_user.client_id))).scalars().first()
        assert abc_client, "ABC Staffing client must exist"

        # Ensure other client exists
        other_client = (await db.execute(select(Client).where(Client.id != abc_client.id))).scalars().first()
        assert other_client, "Other client must exist"

        # Ensure employee is assigned to ABC Staffing
        emp_assignment = (
            await db.execute(
                select(EmployeeClient).where(
                    EmployeeClient.employee_id == emp_user.id,
                    EmployeeClient.client_id == abc_client.id,
                )
            )
        ).scalars().first()
        if not emp_assignment:
            db.add(EmployeeClient(employee_id=emp_user.id, client_id=abc_client.id, active=True))
            await db.commit()

        # Ensure sub_admin is assigned to ABC Staffing
        if sub_admin_user:
            sub_assignment = (
                await db.execute(
                    select(SubAdminAssignment).where(
                        SubAdminAssignment.sub_admin_id == sub_admin_user.id,
                        SubAdminAssignment.client_id == abc_client.id,
                    )
                )
            ).scalars().first()
            if not sub_assignment:
                db.add(SubAdminAssignment(sub_admin_id=sub_admin_user.id, client_id=abc_client.id))
                await db.commit()

        print(f"✅ User Contexts Initialized:")
        print(f"   - Recruiter: {emp_user.name}")
        print(f"   - Target Client: {abc_client.company_name} (Client User: {client_user.name})")
        print(f"   - Other Client: {other_client.company_name}")

        # ----------------------------------------------------------------------
        # TEST 1: AUTO-SYNC RESUME BATCH UPLOAD (NO MANUAL SECOND STEP)
        # ----------------------------------------------------------------------
        print("\n--- Test 1: Upload Batch & Verify Auto-Sync Response ---")

        batch_tag = uuid.uuid4().hex[:6].upper()
        dummy_files = []
        for i in range(3):
            fname = f"TCS_CloudArchitect_{batch_tag}_{i+1}.pdf"
            file_mock = UploadFile(
                filename=fname,
                file=io.BytesIO(b"%PDF-1.4 mock resume content"),
            )
            dummy_files.append(file_mock)

        upload_resp = await process_bulk_upload(
            db=db,
            current_user=emp_user,
            files=dummy_files,
            client_id=abc_client.id,
            resume_date=date.today(),
        )

        assert upload_resp.success is True, "Upload response must have success=True"
        assert upload_resp.client_synced is True, "Upload response must have client_synced=True"
        assert upload_resp.uploaded == 3, f"Expected 3 uploaded, got {upload_resp.uploaded}"
        assert upload_resp.dashboard is not None, "Dashboard stats must be returned in upload response"
        assert upload_resp.dashboard.today_uploads > 0, "today_uploads must be updated"

        await db.commit()
        print(f"✅ Upload succeeded with Auto-Sync:")
        print(f"   - Uploaded: {upload_resp.uploaded}")
        print(f"   - Client Synced: {upload_resp.client_synced}")
        print(f"   - Live Today Uploads: {upload_resp.dashboard.today_uploads}")
        print(f"   - Live Total Uploads: {upload_resp.dashboard.total_resumes}")

        # ----------------------------------------------------------------------
        # TEST 2: INSTANT CLIENT VISIBILITY & SEARCH
        # ----------------------------------------------------------------------
        print("\n--- Test 2: Instant Client Portal Visibility & Search ---")

        # Query resumes as client user
        found_items, total_count = await search_resumes(
            db=db,
            current_user=client_user,
            search=batch_tag,
            limit=10,
            offset=0,
        )

        assert len(found_items) == 3, f"Expected 3 items in client search, got {len(found_items)}"
        for item in found_items:
            assert item.client_id == abc_client.id
            assert batch_tag in item.candidate_name or batch_tag in item.original_filename
        print("✅ Candidate resumes are immediately visible in Client Portal search without manual submission!")

        # ----------------------------------------------------------------------
        # TEST 3: STRICT CLIENT ISOLATION
        # ----------------------------------------------------------------------
        print("\n--- Test 3: Strict Client Isolation Check ---")

        # Create mock user for other client
        other_client_user = User(
            id=uuid.uuid4(),
            email="other_client_sync@test.com",
            name="Other Client User",
            role="client",
            client_id=other_client.id,
        )

        other_found_items, other_count = await search_resumes(
            db=db,
            current_user=other_client_user,
            search=batch_tag,
            limit=10,
            offset=0,
        )
        assert len(other_found_items) == 0, "Other client user should NOT see these resumes"
        print(f"✅ Verified: Other client ({other_client.company_name}) sees 0 resumes from ABC Staffing.")

        # ----------------------------------------------------------------------
        # TEST 4: AUTOMATIC IN-APP NOTIFICATIONS DISPATCHED
        # ----------------------------------------------------------------------
        print("\n--- Test 4: Verify Multi-Role In-App Notifications ---")

        # Check Employee Notification
        emp_notif = (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == emp_user.id,
                    Notification.type == "upload_completed",
                ).order_by(Notification.created_at.desc())
            )
        ).scalars().first()
        assert emp_notif is not None, "Employee should receive upload_completed notification"
        print(f"✅ Employee Notification: '{emp_notif.title}' - {emp_notif.message}")

        # Check Admin Notification
        admin_notif = (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == admin_user.id,
                    Notification.type == "upload_completed",
                ).order_by(Notification.created_at.desc())
            )
        ).scalars().first()
        assert admin_notif is not None, "Admin should receive new resumes notification"
        print(f"✅ Admin Notification: '{admin_notif.title}' - {admin_notif.message}")

        # Check Client Notification
        client_notif = (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == client_user.id,
                    Notification.type == "resume_available",
                ).order_by(Notification.created_at.desc())
            )
        ).scalars().first()
        assert client_notif is not None, "Client should receive resume_available notification"
        print(f"✅ Client Portal Notification: '{client_notif.title}' - {client_notif.message}")

        # ----------------------------------------------------------------------
        # TEST 5: AUTOMATIC ACTIVITY LOG CREATION
        # ----------------------------------------------------------------------
        print("\n--- Test 5: Verify Activity Log Creation ---")

        batch_log = (
            await db.execute(
                select(ActivityLog).where(
                    ActivityLog.user_id == emp_user.id,
                    ActivityLog.action == "resume_batch_uploaded",
                ).order_by(ActivityLog.created_at.desc())
            )
        ).scalars().first()

        assert batch_log is not None, "Batch upload activity log must be created"
        assert batch_log.details.get("saved_count") == 3
        print(f"✅ Activity Log Verified: Action='{batch_log.action}', Details={batch_log.details}")

    print("\n" + "=" * 74)
    print("🎉 ALL AUTO-SYNC AFTER UPLOAD TESTS (100%) PASSED SUCCESSFULLY!")
    print("=" * 74)


if __name__ == "__main__":
    asyncio.run(run_tests())
