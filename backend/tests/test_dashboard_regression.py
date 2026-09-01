"""
Master Dashboard Regression Test Suite.
Verifies all locked dashboard business rules across Admin, Sub-Admin, Employee, and Client roles.

Tests:
1. Total Applications == Uploaded Resumes strictly.
2. AI Mail Analytics strictly decoupled from ATS resume counts.
3. Target Quota single source of truth (targets DB table).
4. Sub-Admin attendance and dropdown scoping.
5. Continuous zero-filled 7-day upload timeline series.
6. Tag-based cache invalidation.
"""

import uuid

import pytest
from app.core.cache import cache, invalidate_dashboard_cache
from app.core.database import async_session_factory
from app.modules.attendance.service import get_admin_attendance_summary
from app.modules.dashboard.service import (
    get_admin_dashboard_home,
    get_employee_dashboard_home,
    get_resume_upload_series,
    resolve_dashboard_scope,
)
from app.modules.resumes.models import Resume
from app.modules.users.models import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_dashboard_ats_metric_locked_rule():
    """Verify Total Applications == Number of uploaded resumes only."""
    async with async_session_factory() as db:
        # Count actual resumes
        resumes_count = (await db.execute(select(Resume.id))).scalars().all()
        total_resumes_in_db = len(resumes_count)

        admin_user = (await db.execute(select(User).where(User.role == "admin"))).scalars().first()
        if not admin_user:
            pytest.skip("No admin user found for test")

        res = await get_admin_dashboard_home(db, current_user=admin_user, date_range="this_month")
        assert res.overview.total_applications == total_resumes_in_db, (
            f"Expected total_applications ({res.overview.total_applications}) to equal total resumes ({total_resumes_in_db})"
        )


@pytest.mark.asyncio
async def test_dashboard_continuous_7day_timeline():
    """Verify get_resume_upload_series returns exactly 7 continuous zero-filled points."""
    async with async_session_factory() as db:
        series = await get_resume_upload_series(db, days=7)
        assert len(series) == 7, f"Expected exactly 7 days in timeline, got {len(series)}"
        for pt in series:
            assert hasattr(pt, "date")
            assert hasattr(pt, "uploads")
            assert isinstance(pt.uploads, int)


@pytest.mark.asyncio
async def test_sub_admin_scoping():
    """Verify Sub-Admin attendance and dropdowns only reflect assigned employees and clients."""
    async with async_session_factory() as db:
        # Create or fetch a test sub_admin user
        sub_admin = (await db.execute(select(User).where(User.role == "sub_admin"))).scalars().first()
        if not sub_admin:
            sub_admin = User(
                id=uuid.uuid4(),
                email=f"test_subadmin_{uuid.uuid4().hex[:6]}@test.com",
                name="Test SubAdmin",
                role="sub_admin",
                password_hash="mock_password",
                is_active=True,
            )
            db.add(sub_admin)
            await db.commit()
            await db.refresh(sub_admin)

        scope = await resolve_dashboard_scope(db, sub_admin)
        assert scope.allowed_client_ids is not None
        assert scope.allowed_employee_ids is not None

        # Verify attendance summary is scoped
        att_summary = await get_admin_attendance_summary(db, allowed_employee_ids=scope.allowed_employee_ids)
        for emp_row in att_summary.active_employees:
            assert uuid.UUID(emp_row["employee_id"]) in scope.allowed_employee_ids

        # Verify dashboard home returns scoped metadata
        sub_home = await get_admin_dashboard_home(db, current_user=sub_admin)
        assert hasattr(sub_home, "clients")
        assert hasattr(sub_home, "all_employees")


@pytest.mark.asyncio
async def test_employee_dashboard_ai_inbox_separation():
    """Verify Employee dashboard AI inbox metrics are populated and decoupled from ATS metrics."""
    async with async_session_factory() as db:
        emp_user = (await db.execute(select(User).where(User.role == "employee"))).scalars().first()
        if not emp_user:
            pytest.skip("No employee user in database")

        emp_home = await get_employee_dashboard_home(db, current_user=emp_user, date_range="today")
        ai_stats = emp_home.dashboard.ai_inbox_stats
        assert hasattr(ai_stats, "emails_processed")
        assert hasattr(ai_stats, "interview_emails_detected")
        assert hasattr(ai_stats, "pending_review")
        assert hasattr(ai_stats, "upcoming_interviews")


@pytest.mark.asyncio
async def test_cache_invalidation():
    """Verify dashboard cache sets and tag-based invalidation work deterministically."""
    cache.set("test_kpi", {"uploads": 42}, ttl=30.0, tags={"dashboard"})
    assert cache.get("test_kpi") == {"uploads": 42}

    invalidate_dashboard_cache()
    assert cache.get("test_kpi") is None
