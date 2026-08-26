import asyncio
import os
import sys
from datetime import date, datetime, timedelta
import uuid
import pytest

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.core.config import settings
from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.targets.models import Target
from app.modules.resumes.service import search_resumes
from app.modules.dashboard.service import (
    get_admin_overview,
    get_employee_dashboard,
    get_client_dashboard,
    get_employee_target_summary,
    _parse_date_filter,
)

from app.core.database import async_session_factory as AsyncSessionLocal


@pytest.mark.anyio
async def test_global_date_filters_and_pipeline():
    print("\n=======================================================")
    print("🚀 RUNNING TEST: Global Custom Date Filters & Auto-Pipeline")
    print("=======================================================\n")

    async with AsyncSessionLocal() as db:
        # Setup Test Users and Client
        admin = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if not admin:
            from app.core.security import hash_password
            admin = User(name=settings.admin_name, email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password), role="admin", is_active=True, status="active")
            db.add(admin)
            await db.flush()

        client = (await db.execute(select(Client))).scalars().first()
        if not client:
            client = Client(company_name="ABC Staffing", contact_person="John Doe", email="contact@abcstaffing.com", phone="+1-555-0101", status="active")
            db.add(client)
            await db.flush()

        employee = (await db.execute(select(User).where(User.role == "employee"))).scalars().first()
        if not employee:
            from app.core.security import hash_password
            employee = User(name="QA Recruiter", email="qa_recruiter@applyflow.com", password_hash=hash_password("Recruiter@123"), role="employee", is_active=True, status="active")
            db.add(employee)
            await db.flush()

        ec = (await db.execute(select(EmployeeClient).where(EmployeeClient.employee_id == employee.id, EmployeeClient.client_id == client.id))).scalar_one_or_none()
        if not ec:
            db.add(EmployeeClient(employee_id=employee.id, client_id=client.id, is_primary=True, active=True))
        await db.commit()

        print(f"✓ Context: Admin={admin.name} ({admin.email}), Employee={employee.name}, Client={client.company_name}")

        test_past_date = date(2026, 8, 20)
        today_date = date.today()

        # 1. Verify Date Parser
        print("\n--- Test 1: Date Filter Parser Helper ---")
        st, en, d = _parse_date_filter("today")
        assert d == today_date, f"Expected today date {today_date}, got {d}"
        print(f"✓ Preset 'today' parsed -> {d}")

        st, en, d = _parse_date_filter("yesterday")
        assert d == today_date - timedelta(days=1), f"Expected yesterday date, got {d}"
        print(f"✓ Preset 'yesterday' parsed -> {d}")

        st, en, d = _parse_date_filter("custom", "2026-08-20")
        assert d == test_past_date, f"Expected {test_past_date}, got {d}"
        print(f"✓ Custom date '2026-08-20' parsed -> {d}")

        # 2. Ingest Historical Resume for 2026-08-20
        print("\n--- Test 2: Ingest Historical Resume (2026-08-20) ---")
        historical_resume = Resume(
            candidate_name="Historical Candidate",
            company="TCS",
            role="Java Developer",
            resume_id_tag="HIST-101",
            client_id=client.id,
            uploaded_by=employee.id,
            resume_date=test_past_date,
            original_filename=f"{client.company_name}_TCS_JavaDeveloper_HIST101.pdf",
        )
        db.add(historical_resume)
        await db.flush()

        historical_app = Application(
            resume_id=historical_resume.id,
            candidate_name="Historical Candidate",
            company="TCS",
            role="Java Developer",
            employee_id=employee.id,
            client_id=client.id,
            status="Submitted",
            applied_date=datetime.combine(test_past_date, datetime.min.time()),
        )
        db.add(historical_app)
        await db.commit()
        print("✓ Created historical resume and application for 2026-08-20")

        # 3. Test Candidate Bank Date Filtering
        print("\n--- Test 3: Candidate Bank Resume Search with Custom Date ---")
        items, total = await search_resumes(
            db,
            current_user=admin,
            client_id=client.id,
            date_filter="custom",
            custom_date="2026-08-20",
        )
        assert any(r.id == historical_resume.id for r in items), "Historical resume not found in custom date search!"
        print(f"✓ Candidate Bank successfully filtered by 2026-08-20: found {len(items)} resumes (Total: {total})")

        # 4. Test Admin Overview Dashboard with Custom Date
        print("\n--- Test 4: Admin Overview Dashboard with Custom Date ---")
        admin_metrics = await get_admin_overview(
            db,
            current_user=admin,
            client_id=client.id,
            custom_date="2026-08-20",
        )
        print(f"✓ Admin Overview (2026-08-20): uploads={admin_metrics.today_uploads}, apps={admin_metrics.today_applications}, completion={admin_metrics.target_completion_pct}%")
        assert admin_metrics.today_uploads >= 1, "Admin overview should include historical resume in uploads"
        assert admin_metrics.today_applications >= 1, "Admin overview should include historical application"

        # 5. Test Employee Dashboard & Single Source Target Summary with Custom Date
        print("\n--- Test 5: Employee Dashboard & Daily Target Quota with Custom Date ---")
        emp_dash = await get_employee_dashboard(
            db,
            user=employee,
            client_id=client.id,
            date_range="custom",
            custom_date="2026-08-20",
        )
        print(f"✓ Employee Dashboard (2026-08-20): uploads={emp_dash.today_uploads}, apps_sent={emp_dash.applications_sent_today}, target_submitted={emp_dash.target_summary.submitted}")
        assert emp_dash.today_uploads >= 1, "Employee dashboard should reflect custom date uploads"
        assert emp_dash.applications_sent_today >= 1, "Employee dashboard should reflect custom date submissions"

        # 6. Test Client Portal Dashboard with Custom Date
        print("\n--- Test 6: Client Portal Dashboard with Custom Date ---")
        client_user_res = await db.execute(select(User).where(User.client_id == client.id))
        client_user = client_user_res.scalars().first()
        if client_user:
            client_dash = await get_client_dashboard(
                db,
                user=client_user,
                date_range="custom",
                custom_date="2026-08-20",
            )
            print(f"✓ Client Portal Dashboard (2026-08-20): applied={client_dash.applied_count}, date_uploads={client_dash.today_uploads}")
            assert client_dash.today_uploads >= 1, "Client portal should calculate uploads on custom date"

        # Cleanup
        await db.delete(historical_app)
        await db.delete(historical_resume)
        await db.commit()
        print("✓ Cleaned up test data.")

    print("\n=======================================================")
    print("🎉 ALL GLOBAL DATE FILTERING & AUTO-PIPELINE TESTS PASSED!")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(test_global_date_filters_and_pipeline())
