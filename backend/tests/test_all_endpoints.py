"""
Comprehensive End-to-End Test Suite for Apply Flow Careers.
Validates:
1. Filename parser for target company, role, and candidate/tag extraction.
2. Authentication & Cookie Token Transport (Admin, Employee Harish, Employee Recruiter2, Client John, Client Sarah).
3. Requirements Listing & Permissions:
   - Admin sees all 8 requirements.
   - Harish sees requirements for ABC Staffing & Talent Hub (6 reqs).
   - Recruiter2 sees requirements for NextHire (2 reqs).
   - John (ABC Staffing) sees only ABC Staffing requirements (3 reqs).
   - Sarah (Talent Hub) sees only Talent Hub requirements (3 reqs).
4. Resume search permission boundaries.
5. Dashboards for all 3 roles (Admin 3 views, Employee workspace, Client customer portal).
6. Multi-tab Excel and ReportLab PDF binary exports.
"""

import pytest
import io
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.modules.resumes.parser import parse_resume_filename


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_filename_parser():
    # Test 1: Target company TCS, Java Developer, Harish
    res1 = parse_resume_filename("TCS_JavaDeveloper_Harish.pdf")
    assert res1["company"] == "TCS"
    assert "Java" in res1["role"]
    assert "Harish" in res1["candidate_name"]

    # Test 2: Target company TCS, Java Developer, RES1023
    res2 = parse_resume_filename("TCS_JavaDeveloper_RES1023.pdf")
    assert res2["company"] == "TCS"
    assert res2["resume_id_tag"] == "RES1023"

    # Test 3: Target company Amazon, Frontend, Resume145
    res3 = parse_resume_filename("Amazon_Frontend_Resume145.pdf")
    assert res3["company"] == "Amazon"
    assert res3["resume_id_tag"] == "RESUME145"


@pytest.mark.asyncio
async def test_admin_flow_and_exports():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin Login
        login_res = await client.post(
            "/api/auth/login",
            json={"email": "admin@applyflow.com", "password": "admin123"},
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "admin"

        # 2. Admin Overview Dashboard
        admin_dash = await client.get("/api/dashboard/admin/overview")
        assert admin_dash.status_code == 200
        data = admin_dash.json()
        assert data["total_clients"] == 3
        assert data["total_requirements"] >= 8
        assert data["total_resumes"] >= 100
        assert data["total_applications"] >= 60

        # 3. Admin Requirements List (all requirements)
        reqs_res = await client.get("/api/requirements")
        assert reqs_res.status_code == 200
        assert len(reqs_res.json()) >= 8

        # 4. Admin Employees View
        emp_view = await client.get("/api/dashboard/admin/employees")
        assert emp_view.status_code == 200
        assert len(emp_view.json()) >= 2

        # 5. Admin Clients View
        client_view = await client.get("/api/dashboard/admin/clients")
        assert client_view.status_code == 200
        assert len(client_view.json()) == 3

        # 6. Excel 3-Sheet Export
        excel_res = await client.get("/api/reports/excel")
        assert excel_res.status_code == 200
        assert len(excel_res.content) > 1000

        # 7. PDF Export
        pdf_res = await client.get("/api/reports/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF")

        # 8. Admin cannot upload resumes (403 Forbidden)
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
        upload_attempt = await client.post(
            "/api/resumes/upload",
            files={"files": ("TCS_Java_Candidate.pdf", fake_pdf, "application/pdf")},
            data={"client_id": str(login_res.json()["user"]["id"])},
        )
        assert upload_attempt.status_code == 403

        # 9. Attendance Summary for Admin
        att_res = await client.get("/api/attendance/admin-summary")
        assert att_res.status_code == 200
        assert "present_today" in att_res.json()

        # 10. Logout
        await client.post("/api/auth/logout")


@pytest.mark.asyncio
async def test_employee_permission_boundary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Log in as Harish (assigned to ABC Staffing & Talent Hub)
        login_res = await client.post(
            "/api/auth/login",
            json={"email": "harish@applyflow.com", "password": "harish123"},
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "employee"

        # Check unique companies list
        comp_res = await client.get("/api/resumes/companies")
        assert comp_res.status_code == 200
        assert len(comp_res.json()) > 0

        # Attendance check-in / status
        att_status = await client.get("/api/attendance/status")
        assert att_status.status_code == 200

        # Notifications list
        notifs_res = await client.get("/api/notifications")
        assert notifs_res.status_code == 200
        assert "unread_count" in notifs_res.json()

        # Harish searches requirements: must only receive ABC Staffing and Talent Hub requirements (not NextHire)
        reqs_res = await client.get("/api/requirements")
        assert reqs_res.status_code == 200
        req_client_names = {r["client_name"] for r in reqs_res.json()}
        assert "ABC Staffing" in req_client_names or "Talent Hub" in req_client_names
        assert "NextHire" not in req_client_names

        # Harish searches resumes: must only receive ABC Staffing and Talent Hub resumes
        res_list = await client.get("/api/resumes")
        assert res_list.status_code == 200
        resume_clients = {item["client_name"] for item in res_list.json()["items"]}
        assert "NextHire" not in resume_clients

        # Harish Employee Dashboard with date filter
        emp_dash = await client.get("/api/dashboard/employee?date_range=this_week")
        assert emp_dash.status_code == 200
        dash_data = emp_dash.json()
        assert dash_data["assigned_clients_count"] == 2
        assert len(dash_data["client_requirements"]) > 0

        # Logout Harish
        await client.post("/api/auth/logout")

        # 2. Log in as Recruiter2 (assigned to NextHire)
        login_r2 = await client.post(
            "/api/auth/login",
            json={"email": "recruiter2@applyflow.com", "password": "recruiter123"},
        )
        assert login_r2.status_code == 200

        # Recruiter2 requirements must only be NextHire
        r2_reqs = await client.get("/api/requirements")
        assert r2_reqs.status_code == 200
        r2_clients = {r["client_name"] for r in r2_reqs.json()}
        assert r2_clients == {"NextHire"}

        # Recruiter2 resumes must only be NextHire
        r2_resumes = await client.get("/api/resumes")
        assert r2_resumes.status_code == 200
        for item in r2_resumes.json()["items"]:
            assert item["client_name"] == "NextHire"

        # Logout Recruiter2
        await client.post("/api/auth/logout")


@pytest.mark.asyncio
async def test_client_portal_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Log in as John (ABC Staffing)
        login_res = await client.post(
            "/api/auth/login",
            json={"email": "john@abcstaffing.com", "password": "client123"},
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "client"

        # Dashboard: ABC Staffing
        dash_res = await client.get("/api/dashboard/client")
        assert dash_res.status_code == 200
        assert dash_res.json()["company_name"] == "ABC Staffing"
        assert dash_res.json()["active_requirements_count"] == 3

        # Requirements: only ABC Staffing
        reqs_res = await client.get("/api/requirements")
        assert reqs_res.status_code == 200
        for req in reqs_res.json():
            assert req["client_name"] == "ABC Staffing"

        # Resumes: only ABC Staffing
        resumes_res = await client.get("/api/resumes")
        assert resumes_res.status_code == 200
        for item in resumes_res.json()["items"]:
            assert item["client_name"] == "ABC Staffing"

        # Logout John
        await client.post("/api/auth/logout")

        # 2. Log in as Sarah (Talent Hub)
        login_sarah = await client.post(
            "/api/auth/login",
            json={"email": "sarah@talenthub.com", "password": "client123"},
        )
        assert login_sarah.status_code == 200

        # Dashboard: Talent Hub
        dash_sarah = await client.get("/api/dashboard/client")
        assert dash_sarah.status_code == 200
        assert dash_sarah.json()["company_name"] == "Talent Hub"
        assert dash_sarah.json()["active_requirements_count"] == 3

        # Requirements: only Talent Hub
        sarah_reqs = await client.get("/api/requirements")
        assert sarah_reqs.status_code == 200
        for req in sarah_reqs.json():
            assert req["client_name"] == "Talent Hub"
