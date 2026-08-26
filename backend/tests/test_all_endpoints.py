"""
Comprehensive End-to-End Test Suite for ApplyFlow ATS.
Validates:
1. Filename parser for ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf format.
2. Production Super Admin Authentication & Profile verification.
3. Health check, overview metrics, and Excel/PDF reporting endpoints.
4. Role permission isolation and security boundaries.
"""

import pytest
import io
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.resumes.parser import parse_resume_filename


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_filename_parser():
    # Test 1: ServiceClient=ABCStaffing, Company=TCS, Role=JavaDeveloper, ID=RES101
    res1 = parse_resume_filename("ABCStaffing_TCS_JavaDeveloper_RES101.pdf")
    assert "ABC Staffing" in res1["service_client"] or res1["service_client"] == "ABCStaffing"
    assert res1["company"] == "TCS"
    assert "Java" in res1["role"]
    assert res1["resume_id_tag"] == "RES101"

    # Test 2: ServiceClient=TalentHub, Company=Amazon, Role=SDEII, ID=RES205
    res2 = parse_resume_filename("TalentHub_Amazon_SDEII_RES205.pdf")
    assert "Talent" in res2["service_client"]
    assert res2["company"] == "Amazon"
    assert "SDE" in res2["role"]
    assert res2["resume_id_tag"] == "RES205"

    # Test 3: ServiceClient=NextHire, Company=Infosys, Role=INF-PY-02, Candidate=RahulKumar
    res3 = parse_resume_filename("NextHire_Infosys_INF-PY-02_RahulKumar.pdf")
    assert "Next" in res3["service_client"]
    assert res3["company"] == "Infosys"
    assert res3["role"] == "INF-PY-02"
    assert res3["candidate_name"] == "Rahul Kumar"


@pytest.mark.anyio
async def test_admin_flow_and_exports():
    # Ensure Super Admin exists in DB with correct password
    async with async_session_factory() as db:
        admin_user = (await db.execute(select(User).where(User.email.ilike(settings.admin_email)))).scalars().first()
        if not admin_user:
            admin_user = User(
                name=settings.admin_name,
                email=settings.admin_email.lower(),
                password_hash=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
                status="active",
            )
            db.add(admin_user)
        else:
            admin_user.password_hash = hash_password(settings.admin_password)
            admin_user.is_active = True
            admin_user.status = "active"
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin Login with production credentials
        login_res = await client.post(
            "/api/auth/login",
            json={"email": settings.admin_email, "password": settings.admin_password},
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "admin"
        assert login_res.json()["user"]["email"].lower() == settings.admin_email.lower()

        # 2. Admin Overview Dashboard
        admin_dash = await client.get("/api/dashboard/admin/overview")
        assert admin_dash.status_code == 200

        # 3. Excel Report Export
        excel_res = await client.get("/api/reports/excel")
        assert excel_res.status_code == 200

        # 4. PDF Report Export
        pdf_res = await client.get("/api/reports/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF")

        # 5. Admin cannot upload resumes (Recruiter-only security boundary)
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
        upload_attempt = await client.post(
            "/api/resumes/upload",
            files={"files": ("Test_TCS_Java_RES101.pdf", fake_pdf, "application/pdf")},
            data={"client_id": str(login_res.json()["user"]["id"])},
        )
        assert upload_attempt.status_code == 403

        # 6. Logout
        logout_res = await client.post("/api/auth/logout")
        assert logout_res.status_code == 200


@pytest.mark.anyio
async def test_unauthenticated_security_boundaries():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request to admin overview blocked
        dash_res = await client.get("/api/dashboard/admin/overview")
        assert dash_res.status_code in [401, 403]

        # 2. Unauthenticated request to /api/auth/me blocked
        me_res = await client.get("/api/auth/me")
        assert me_res.status_code in [401, 403]

        # 3. Health check is publicly accessible
        health_res = await client.get("/api/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"
