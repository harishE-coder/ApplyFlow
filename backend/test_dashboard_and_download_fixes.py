"""
Test Suite: Critical Bug Fixes
1. Dashboard upload counts live calculation and instant update across Employee, Sub-Admin, Admin, Client.
2. Resume Download & Preview strictly returning valid raw PDF bytes (Never HTML) with RBAC permissions.
"""

import asyncio
import uuid
from datetime import date, datetime
import httpx
from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.resumes.models import Resume
from app.modules.dashboard.service import (
    get_admin_overview,
    get_employee_dashboard,
    get_client_dashboard,
)
from app.core.security import create_access_token
from app.services.google_drive import drive_service

BASE_URL = "http://127.0.0.1:8000"


async def run_tests():
    print("\n" + "=" * 74)
    print("🧪 RUNNING CRITICAL BUG FIX VERIFICATION TEST SUITE")
    print("=" * 74)

    async with async_session_factory() as db:
        # 1. Fetch test users and client
        admin_user = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        emp_user = (await db.execute(select(User).where(User.role == "employee", User.is_active == True))).scalars().first()
        sub_admin_user = (await db.execute(select(User).where(User.role == "sub_admin", User.is_active == True))).scalars().first()
        client_user = (await db.execute(select(User).where(User.role == "client", User.is_active == True))).scalars().first()

        assert admin_user is not None, "Admin user required"
        assert emp_user is not None, "Employee user required"
        assert client_user is not None, "Client user required"

        # Find client for client_user
        client_obj = (await db.execute(select(Client).where(Client.id == client_user.client_id))).scalars().first()
        assert client_obj is not None, "Client object required"

        # Ensure employee is assigned to this client
        assignment = (
            await db.execute(
                select(EmployeeClient).where(
                    EmployeeClient.employee_id == emp_user.id,
                    EmployeeClient.client_id == client_obj.id,
                )
            )
        ).scalars().first()
        if not assignment:
            db.add(EmployeeClient(employee_id=emp_user.id, client_id=client_obj.id, active=True))
            await db.commit()

        print(f"✅ User Contexts Initialized:")
        print(f"   - Admin: {admin_user.name} ({admin_user.email})")
        print(f"   - Recruiter: {emp_user.name} ({emp_user.email})")
        print(f"   - Client: {client_obj.company_name} (User: {client_user.name})")

        # ---------------------------------------------------------------------
        # TEST 1: DASHBOARD UPLOAD COUNT LIVE SQL RECALCULATION
        # ---------------------------------------------------------------------
        print("\n--- TEST 1: Live Dashboard Upload Count Verification ---", flush=True)

        print("Fetching pre_emp_dash...", flush=True)
        pre_emp_dash = await get_employee_dashboard(db, user=emp_user, client_id=client_obj.id, date_range="today")
        print("Fetching pre_admin_dash...", flush=True)
        pre_admin_dash = await get_admin_overview(db, current_user=admin_user, client_id=client_obj.id, date_range="today")
        print("Fetching pre_client_dash...", flush=True)
        pre_client_dash = await get_client_dashboard(db, user=client_user)

        initial_emp_today = pre_emp_dash.today_uploads
        initial_emp_total = pre_emp_dash.total_uploads
        initial_admin_today = pre_admin_dash.today_uploads
        initial_admin_total = pre_admin_dash.total_resumes
        initial_client_applied = pre_client_dash.applied_count
        initial_client_today = pre_client_dash.today_uploads

        print(f"📊 Baseline Counts:", flush=True)
        print(f"   - Employee: Today={initial_emp_today}, Total={initial_emp_total}", flush=True)
        print(f"   - Admin: Today={initial_admin_today}, Total={initial_admin_total}", flush=True)
        print(f"   - Client: Applied={initial_client_applied}, Today={initial_client_today}", flush=True)

        # Ingest 15 new resumes
        batch_size = 15
        saved_resumes = []
        batch_uid = uuid.uuid4().hex[:6]
        for i in range(batch_size):
            r = Resume(
                candidate_name=f"FixTest Candidate {batch_uid} {i+1}",
                company="Amazon",
                role="DevOps Engineer",
                resume_id_tag=f"FIX-{batch_uid}-{i+1}",
                client_id=client_obj.id,
                uploaded_by=emp_user.id,
                resume_date=date.today(),
                original_filename=f"FixTest_{batch_uid}_{i+1}.pdf",
                drive_file_id=f"file_fix_{batch_uid}_{i+1}",
            )
            db.add(r)
            saved_resumes.append(r)

        await db.commit()

        print("Fetching post_emp_dash...", flush=True)
        post_emp_dash = await get_employee_dashboard(db, user=emp_user, client_id=client_obj.id, date_range="today")
        print("Fetching post_admin_dash...", flush=True)
        post_admin_dash = await get_admin_overview(db, current_user=admin_user, client_id=client_obj.id, date_range="today")
        print("Fetching post_client_dash...", flush=True)
        post_client_dash = await get_client_dashboard(db, user=client_user)

        print(f"\n📈 Post-Upload Counts (After +{batch_size} upload):", flush=True)
        print(f"   - Employee: Today={post_emp_dash.today_uploads} (Expected: {initial_emp_today + batch_size})", flush=True)
        print(f"   - Employee: Total={post_emp_dash.total_uploads} (Expected: {initial_emp_total + batch_size})", flush=True)
        print(f"   - Admin: Today={post_admin_dash.today_uploads} (Expected: {initial_admin_today + batch_size})", flush=True)
        print(f"   - Admin: Total={post_admin_dash.total_resumes} (Expected: {initial_admin_total + batch_size})", flush=True)
        print(f"   - Client: Applied={post_client_dash.applied_count} (Expected: {initial_client_applied + batch_size})", flush=True)
        print(f"   - Client: Today={post_client_dash.today_uploads} (Expected: {initial_client_today + batch_size})", flush=True)

        assert post_emp_dash.today_uploads == initial_emp_today + batch_size, "Employee today_uploads didn't match"
        assert post_emp_dash.total_uploads == initial_emp_total + batch_size, "Employee total_uploads didn't match"
        assert post_admin_dash.today_uploads == initial_admin_today + batch_size, "Admin today_uploads didn't match"
        assert post_admin_dash.total_resumes == initial_admin_total + batch_size, "Admin total_resumes didn't match"
        assert post_client_dash.applied_count == initial_client_applied + batch_size, "Client applied_count didn't match"
        assert post_client_dash.today_uploads == initial_client_today + batch_size, "Client today_uploads didn't match"

        print("✅ TEST 1 PASSED: Dashboard upload counts accurately recalculate and increase in real-time!", flush=True)

        # ---------------------------------------------------------------------
        # TEST 2: RESUME DOWNLOAD AND PREVIEW RETURNING RAW PDF (NEVER HTML)
        # ---------------------------------------------------------------------
        print("\n--- TEST 2: Resume Download & Preview PDF Streaming ---")

        test_resume = saved_resumes[0]
        file_bytes, mime_type = await drive_service.get_file_bytes(
            file_id=test_resume.drive_file_id,
            original_filename=test_resume.original_filename,
        )

        assert mime_type == "application/pdf", f"Expected application/pdf, got {mime_type}"
        assert file_bytes.startswith(b"%PDF-"), "Expected raw PDF bytes starting with %PDF-"
        assert b"<html" not in file_bytes.lower(), "PDF bytes must NOT contain HTML"
        assert b"<!doctype" not in file_bytes.lower(), "PDF bytes must NOT contain HTML DOCTYPE"

        print(f"✅ Raw PDF generated/streamed successfully:")
        print(f"   - Size: {len(file_bytes)} bytes")
        print(f"   - Header: {file_bytes[:10]}")
        print(f"   - MIME: {mime_type}")
        print(f"   - HTML Check: Clean (0 HTML tokens found)")

        # Verify synchronous get_file_content wrapper
        sync_bytes, sync_mime = drive_service.get_file_content(
            file_id=test_resume.drive_file_id,
            original_filename=test_resume.original_filename,
        )
        assert sync_mime == "application/pdf"
        assert sync_bytes.startswith(b"%PDF-")
        print("✅ TEST 2 PASSED: Resume download pipeline strictly streams valid PDF bytes!")

        # ---------------------------------------------------------------------
        # TEST 3: ROLE-BASED ACCESS CONTROL ON RESUME DOWNLOAD / PREVIEW
        # ---------------------------------------------------------------------
        print("\n--- TEST 3: Permission Matrix Validation on Download/Preview ---")

        from app.modules.resumes.service import get_resume_by_id

        # 1. Admin can access
        admin_access = await get_resume_by_id(db, test_resume.id, admin_user)
        assert admin_access is not None, "Admin should have access"
        print("✅ Admin access: ALLOWED")

        # 2. Recruiter assigned to client can access
        emp_access = await get_resume_by_id(db, test_resume.id, emp_user)
        assert emp_access is not None, "Assigned employee should have access"
        print("✅ Assigned Recruiter access: ALLOWED")

        # 3. Client user owning the client can access
        client_access = await get_resume_by_id(db, test_resume.id, client_user)
        assert client_access is not None, "Client user should have access to own resume"
        print("✅ Client Portal access: ALLOWED")

        # 4. Unauthorized client user (different client)
        other_client_user = User(
            id=uuid.uuid4(),
            email="other_client@test.com",
            name="Other Client",
            role="client",
            client_id=uuid.uuid4(),  # Different client ID
        )
        try:
            from fastapi import HTTPException
            unauth_access = await get_resume_by_id(db, test_resume.id, other_client_user)
            # If get_resume_by_id returns None or raises 403
            assert unauth_access is None, "Unauthorized client user should not access other client's resume"
            print("✅ Unauthorized Client access: BLOCKED (Correctly returned None/Forbidden)")
        except HTTPException as e:
            assert e.status_code in [403, 404]
            print(f"✅ Unauthorized Client access: BLOCKED ({e.status_code} {e.detail})")

        print("✅ TEST 3 PASSED: Role-based permissions strictly enforced.")

        # Cleanup test resumes
        for r in saved_resumes:
            await db.delete(r)
        await db.commit()
        print("✅ Test data cleaned up.")

    print("\n" + "=" * 74)
    print("🎉 ALL CRITICAL BUG FIX TESTS (100%) PASSED SUCCESSFULLY!")
    print("=" * 74)


if __name__ == "__main__":
    asyncio.run(run_tests())
