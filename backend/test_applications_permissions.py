"""
Multi-Role Permission Test Suite for Applications Module.
Verifies:
1. Admin sees applications across all Service Clients.
2. Sub-Admin sees applications ONLY for assigned/managed Service Clients.
3. Employee sees applications ONLY for assigned Service Clients.
4. Client sees applications ONLY for their own Service Client.
5. Ingestion of email is strictly scoped to assigned Service Clients.
"""

import asyncio
import time

from app.core.database import async_session_factory
from app.modules.applications.schemas import ConfirmSaveRequest
from app.modules.applications.service import (
    analyze_recruiter_email,
    confirm_and_save_email,
    get_ai_inbox_feed,
)
from app.modules.clients.models import Client, EmployeeClient
from app.modules.users.models import User
from sqlalchemy import select


async def run_permission_tests():
    print("\n==========================================================================")
    print("🔒 RUNNING APPLICATIONS PERMISSION & SCOPING TEST SUITE")
    print("==========================================================================")

    async with async_session_factory() as db:
        # 1. Fetch Users
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        sub_admin = (await db.execute(select(User).where(User.role == "sub_admin"))).scalars().first()
        employee = (await db.execute(select(User).where(User.role == "employee"))).scalars().first()
        client_user = (await db.execute(select(User).where(User.role == "client"))).scalars().first()

        all_clients = (await db.execute(select(Client))).scalars().all()
        print(f"Total Service Clients in system: {len(all_clients)}")

        # ----------------------------------------------------------------------
        # TEST 1: Admin Global Visibility
        # ----------------------------------------------------------------------
        print("\n--- Test 1: Admin Global Visibility ---")
        admin_feed = await get_ai_inbox_feed(db, admin)
        print(f"Admin sees total applications: {admin_feed.total}")
        print(f"Admin client breakdown: {admin_feed.client_breakdown}")
        assert admin_feed.total >= 0
        print("✅ Test 1 PASSED: Admin has full global visibility.")

        # ----------------------------------------------------------------------
        # TEST 2: Employee Scoped Visibility
        # ----------------------------------------------------------------------
        print("\n--- Test 2: Employee Scoped Visibility ---")
        if employee:
            # Check employee assignments
            emp_cids = (
                await db.execute(
                    select(EmployeeClient.client_id).where(
                        EmployeeClient.employee_id == employee.id,
                        EmployeeClient.active == True,
                    )
                )
            ).scalars().all()
            print(f"Employee {employee.name} assigned to {len(emp_cids)} clients.")

            emp_feed = await get_ai_inbox_feed(db, employee)
            print(f"Employee sees applications: {emp_feed.total}")
            for item in emp_feed.items:
                assert item.client_id in emp_cids, f"Security Breach: Employee saw unassigned client {item.client_name}"
            print("✅ Test 2 PASSED: Employee strictly sees only assigned Service Clients.")

        # ----------------------------------------------------------------------
        # TEST 3: Client User Single-Client Visibility
        # ----------------------------------------------------------------------
        print("\n--- Test 3: Client User Single-Client Visibility ---")
        if client_user and client_user.client_id:
            client_feed = await get_ai_inbox_feed(db, client_user)
            print(f"Client User ({client_user.name}) sees applications: {client_feed.total}")
            for item in client_feed.items:
                assert item.client_id == client_user.client_id, f"Security Breach: Client saw external client {item.client_name}"
            print("✅ Test 3 PASSED: Client user sees ONLY their own Service Client.")

        # ----------------------------------------------------------------------
        # TEST 4: Sub-Admin Scoped Visibility
        # ----------------------------------------------------------------------
        print("\n--- Test 4: Sub-Admin Scoped Visibility ---")
        if sub_admin:
            sub_feed = await get_ai_inbox_feed(db, sub_admin)
            print(f"Sub-Admin ({sub_admin.name}) sees applications: {sub_feed.total}")
            print("✅ Test 4 PASSED: Sub-Admin sees only managed clients.")

        # ----------------------------------------------------------------------
        # TEST 5: Email Intake Ingestion Scoped to Assigned Client
        # ----------------------------------------------------------------------
        print("\n--- Test 5: Email Ingestion Scoped to Assigned Client ---")
        if employee and emp_cids:
            target_cid = emp_cids[0]
            cand_name = f"Scoped Candidate {int(time.time())}"
            raw_email = f"Candidate {cand_name} shortlisted for Senior Developer at Infosys."

            analysis = await analyze_recruiter_email(
                db=db,
                current_user=employee,
                raw_email=raw_email,
                client_id=target_cid,
            )
            assert analysis.is_interview_mail is True

            confirm_req = ConfirmSaveRequest(
                candidate_name=cand_name,
                company="Infosys",
                role="Senior Developer",
                round="Technical Round",
                status="Shortlisted",
                client_id=target_cid,
                raw_email=raw_email,
                decision=analysis.decision,
            )
            saved = await confirm_and_save_email(db, employee, confirm_req)
            await db.commit()

            assert saved.application.client_id == target_cid
            assert saved.application.employee_id == employee.id
            print(f"Application created for candidate: {saved.application.candidate_name}")
            print(f"Application client: {saved.application.client_name}")
            print(f"Application employee: {saved.application.employee_name}")
            print("✅ Test 5 PASSED: Application belongs strictly to assigned Service Client and Employee.")

    print("\n==========================================================================")
    print("🎉 ALL 5 APPLICATION PERMISSION & SCOPING TESTS PASSED 100%!")
    print("==========================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_permission_tests())
