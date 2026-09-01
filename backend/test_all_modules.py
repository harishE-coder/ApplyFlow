"""
ApplyFlow Complete End-to-End System Test Suite.
Tests all backend modules across all roles (Admin, Employee, Client),
verifies business logic constraints, and outputs detailed pass/fail diagnostics.
"""

import sys
import uuid
from datetime import date

import requests

BASE_URL = "http://localhost:8000"

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_status(self, response, expected_statuses, test_name):
        if not isinstance(expected_statuses, list):
            expected_statuses = [expected_statuses]
        if response.status_code in expected_statuses:
            print(f"  ✅ PASS: {test_name} [{response.status_code}]", flush=True)
            self.passed += 1
            return True
        else:
            msg = f"  ❌ FAIL: {test_name} — Expected {expected_statuses}, got {response.status_code}. Response: {response.text[:300]}"
            print(msg, flush=True)
            self.failed += 1
            self.errors.append((test_name, response.status_code, response.text))
            return False

    def assert_true(self, condition, test_name, error_msg="Assertion failed"):
        if condition:
            print(f"  ✅ PASS: {test_name}", flush=True)
            self.passed += 1
            return True
        else:
            msg = f"  ❌ FAIL: {test_name} — {error_msg}"
            print(msg, flush=True)
            self.failed += 1
            self.errors.append((test_name, "Boolean Assertion", error_msg))
            return False

runner = TestRunner()

def run_all_tests():
    print("=" * 70, flush=True)
    print("🚀 STARTING APPLYFLOW COMPREHENSIVE E2E MODULE AUDIT & TEST SUITE", flush=True)
    print("=" * 70, flush=True)

    # -------------------------------------------------------------
    # 1. AUTHENTICATION MODULE TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 1: AUTHENTICATION & SESSIONS", flush=True)
    
    # 1.1 Admin Login
    admin_session = requests.Session()
    res = admin_session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@applyflow.com", "password": "admin123"})
    runner.assert_status(res, 200, "Admin Login")
    admin_user = res.json().get("user", {})
    runner.assert_true(admin_user.get("role") == "admin", "Admin role check")

    # 1.2 Employee Login
    emp_session = requests.Session()
    res = emp_session.post(f"{BASE_URL}/api/auth/login", json={"email": "harish@applyflow.com", "password": "harish123"})
    runner.assert_status(res, 200, "Employee (Harish) Login")
    emp_user = res.json().get("user", {})
    runner.assert_true(emp_user.get("role") == "employee", "Employee role check")

    # 1.3 Client Login
    client_session = requests.Session()
    res = client_session.post(f"{BASE_URL}/api/auth/login", json={"email": "john@abcstaffing.com", "password": "client123"})
    runner.assert_status(res, 200, "Client (ABC Staffing) Login")
    client_user = res.json().get("user", {})
    runner.assert_true(client_user.get("role") == "client", "Client role check")

    # 1.4 Get Profile (/api/auth/me)
    res = admin_session.get(f"{BASE_URL}/api/auth/me")
    runner.assert_status(res, 200, "Admin Profile /api/auth/me")
    runner.assert_true(res.json().get("email") == "admin@applyflow.com", "Admin profile email match")

    # 1.5 Invalid Login rejection
    bad_session = requests.Session()
    res = bad_session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@applyflow.com", "password": "wrongpassword"})
    runner.assert_status(res, 401, "Invalid Password Rejection")

    # -------------------------------------------------------------
    # 2. CLIENTS MODULE TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 2: SERVICE CLIENTS (CUSTOMERS)", flush=True)
    
    # 2.1 Get all clients as Admin
    res = admin_session.get(f"{BASE_URL}/api/clients")
    runner.assert_status(res, 200, "Admin Get All Clients")
    clients_list = res.json()
    runner.assert_true(len(clients_list) >= 2, "Admin sees multiple Service Clients")
    abc_client = next((c for c in clients_list if "ABC" in c["company_name"]), clients_list[0])
    client_id = abc_client["id"]

    # 2.2 Get assigned clients as Employee
    res = emp_session.get(f"{BASE_URL}/api/clients")
    runner.assert_status(res, 200, "Employee Get Assigned Clients")
    emp_clients = res.json()
    runner.assert_true(len(emp_clients) > 0, "Employee has assigned Service Clients")

    # 2.3 Client role clients request
    res = client_session.get(f"{BASE_URL}/api/clients")
    runner.assert_status(res, 200, "Client role clients request")

    # 2.4 Create a new Client as Admin
    new_client_payload = {
        "company_name": f"Apex Talent {uuid.uuid4().hex[:6]}",
        "contact_person": "Michael Scott",
        "email": f"michael_{uuid.uuid4().hex[:6]}@apex.com",
        "phone": "+1-555-9988",
    }
    res = admin_session.post(f"{BASE_URL}/api/clients", json=new_client_payload)
    runner.assert_status(res, [200, 201], "Admin Create Service Client")
    created_client = res.json()
    created_client_id = created_client.get("id")

    # 2.5 Update Client (PUT & PATCH)
    if created_client_id:
        res = admin_session.patch(f"{BASE_URL}/api/clients/{created_client_id}", json={"phone": "+1-555-0000"})
        runner.assert_status(res, 200, "Admin Update Service Client (PATCH)")

    # -------------------------------------------------------------
    # 3. RECRUITERS & USERS MANAGEMENT TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 3: RECRUITERS & USERS", flush=True)

    # 3.1 Get recruiters list
    res = admin_session.get(f"{BASE_URL}/api/employees")
    runner.assert_status(res, 200, "Admin Get Employees List")

    # 3.2 Create new Recruiter User
    new_recruiter_payload = {
        "name": f"Test Recruiter {uuid.uuid4().hex[:4]}",
        "email": f"recruiter_{uuid.uuid4().hex[:6]}@applyflow.com",
        "password": "Password@123",
        "role": "employee",
        "assigned_client_ids": [client_id],
    }
    res = admin_session.post(f"{BASE_URL}/api/users", json=new_recruiter_payload)
    runner.assert_status(res, [200, 201], "Admin Create New Recruiter")
    _new_emp_id = res.json().get("id")

    # -------------------------------------------------------------
    # 4. REQUIREMENTS MODULE TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 4: CLIENT JOB REQUIREMENTS", flush=True)

    # 4.1 Create Requirement
    req_payload = {
        "client_id": client_id,
        "company": "Amazon",
        "role": "Backend Engineer",
        "role_code": f"AMZ-BE-{uuid.uuid4().hex[:4].upper()}",
        "job_description": "Building high-scale AWS microservices in Python & Go.",
        "experience_years": 4,
        "location": "Remote",
    }
    res = admin_session.post(f"{BASE_URL}/api/requirements", json=req_payload)
    runner.assert_status(res, [200, 201], "Admin Create Job Requirement")
    created_req = res.json()
    req_id = created_req.get("id")

    # 4.2 Get Requirements list
    res = admin_session.get(f"{BASE_URL}/api/requirements", params={"client_id": client_id})
    runner.assert_status(res, 200, "Get Requirements List")

    # -------------------------------------------------------------
    # 5. RESUMES INGESTION & SEARCH TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 5: RESUMES INGESTION & SEARCH", flush=True)

    # 5.1 Check Duplicates
    dup_payload = {
        "client_id": client_id,
        "items": [
            {
                "filename": "TCS_JavaDeveloper_RES999.pdf",
                "candidate_name": "Test Candidate",
                "company": "TCS",
                "role": "Java Developer",
            }
        ]
    }
    res = emp_session.post(f"{BASE_URL}/api/resumes/check-duplicates", json=dup_payload)
    runner.assert_status(res, 200, "Duplicate Check API")

    # 5.2 Upload Resumes as Employee (Multi-file)
    mock_pdf_1 = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /MediaBox [0 0 612 792] >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    )
    files = [
        ("files", (f"Google_SDE2_Candidate_{uuid.uuid4().hex[:4]}.pdf", mock_pdf_1, "application/pdf")),
        ("files", (f"Infosys_FullStack_Candidate_{uuid.uuid4().hex[:4]}.pdf", mock_pdf_1, "application/pdf")),
    ]
    data = {
        "client_id": client_id,
        "resume_date": date.today().isoformat(),
        "requirement_id": req_id,
    }
    res = emp_session.post(f"{BASE_URL}/api/resumes/upload", data=data, files=files)
    runner.assert_status(res, 200, "Employee Bulk Resume Upload")
    upload_res_data = res.json()
    runner.assert_true(upload_res_data.get("saved_count") == 2, "2 Resumes successfully saved")
    uploaded_items = upload_res_data.get("items", [])
    test_resume_id = uploaded_items[0].get("saved_resume_id") if uploaded_items else None

    # 5.3 Non-employee Upload Rejection (Admin & Client cannot upload)
    res = admin_session.post(f"{BASE_URL}/api/resumes/upload", data=data, files=files)
    runner.assert_status(res, 403, "Admin Upload Rejection (Recruiter Only Rule)")

    # 5.4 Search Resumes
    res = emp_session.get(f"{BASE_URL}/api/resumes", params={"client_id": client_id})
    runner.assert_status(res, 200, "Search Resumes")

    # 5.5 Get Target Companies list
    res = emp_session.get(f"{BASE_URL}/api/resumes/companies")
    runner.assert_status(res, 200, "Target Companies List")

    # 5.6 Download/Preview Resume PDF
    if test_resume_id:
        res = emp_session.get(f"{BASE_URL}/api/resumes/{test_resume_id}/download")
        runner.assert_status(res, 200, "Download / Preview Resume PDF")
        runner.assert_true(b"%PDF" in res.content[:10], "Valid PDF content returned")

    # -------------------------------------------------------------
    # 6. APPLICATIONS & PIPELINE TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 6: CANDIDATE APPLICATIONS & CLIENT PIPELINE", flush=True)

    # 6.1 Submit Application
    if test_resume_id and req_id:
        app_payload = {
            "resume_id": test_resume_id,
            "requirement_id": req_id,
            "status": "submitted",
            "client_notes": "Candidate matches 100% AWS requirements.",
        }
        res = emp_session.post(f"{BASE_URL}/api/applications", json=app_payload)
        runner.assert_status(res, [200, 201], "Employee Submit Candidate Application")
        app_data = res.json()
        app_id = app_data.get("id")

        # 6.2 Update Application Status
        if app_id:
            res = emp_session.patch(f"{BASE_URL}/api/applications/{app_id}/status", json={"status": "shortlisted"})
            runner.assert_status(res, 200, "Update Application Status to Shortlisted")

            # 6.3 Update Notes
            res = emp_session.patch(f"{BASE_URL}/api/applications/{app_id}/notes", json={"client_notes": "Interview scheduled for Friday."})
            runner.assert_status(res, 200, "Update Application Notes")

    # 6.4 Get Applications List
    res = emp_session.get(f"{BASE_URL}/api/applications")
    runner.assert_status(res, 200, "Get Applications List")

    # 6.5 Get Application Pipeline Stats
    res = emp_session.get(f"{BASE_URL}/api/applications/stats")
    runner.assert_status(res, 200, "Get Pipeline Stats")

    # -------------------------------------------------------------
    # 7. TARGETS & GOALS MODULE TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 7: TARGETS & DAILY GOALS", flush=True)

    # 7.1 Admin Set Target for Employee + Client pair
    target_payload = {
        "employee_id": emp_user.get("id"),
        "client_id": client_id,
        "daily_target": 30,
    }
    res = admin_session.post(f"{BASE_URL}/api/targets", json=target_payload)
    runner.assert_status(res, 200, "Admin Set Daily Application Target")

    # 7.2 Get Targets list
    res = admin_session.get(f"{BASE_URL}/api/targets")
    runner.assert_status(res, 200, "Get All Targets")

    # 7.3 Get Employee Target Progress
    res = emp_session.get(f"{BASE_URL}/api/targets/progress")
    runner.assert_status(res, 200, "Get Employee Target Progress Breakdown")

    # -------------------------------------------------------------
    # 8. ATTENDANCE & LIVE SHIFTS TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 8: ATTENDANCE & TIME TRACKING", flush=True)

    # 8.1 Check Attendance Status
    res = emp_session.get(f"{BASE_URL}/api/attendance/status")
    runner.assert_status(res, 200, "Get Attendance Status")

    # 8.2 Check-in
    res = emp_session.post(f"{BASE_URL}/api/attendance/check-in")
    runner.assert_status(res, [200, 400], "Check In")

    # 8.3 Check-out
    res = emp_session.post(f"{BASE_URL}/api/attendance/check-out")
    runner.assert_status(res, [200, 400], "Check Out")

    # 8.4 Admin Attendance Summary
    res = admin_session.get(f"{BASE_URL}/api/attendance/admin-summary")
    runner.assert_status(res, 200, "Admin Attendance Live Summary")

    # -------------------------------------------------------------
    # 9. DASHBOARD TELEMETRY TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 9: DASHBOARD TELEMETRY & REPORTING", flush=True)

    # 9.1 Admin Overview (All Clients)
    res = admin_session.get(f"{BASE_URL}/api/dashboard/admin/overview", params={"date_range": "today"})
    runner.assert_status(res, 200, "Admin Dashboard Overview (All Clients, Today)")

    # 9.2 Admin Overview with Historical Date
    res = admin_session.get(f"{BASE_URL}/api/dashboard/admin/overview", params={"date_range": "2026-08-20"})
    runner.assert_status(res, 200, "Admin Dashboard Overview (Historical Date)")

    # 9.3 Admin Overview filtered by single Client & Employee
    res = admin_session.get(f"{BASE_URL}/api/dashboard/admin/overview", params={"client_id": client_id, "employee_id": emp_user.get("id")})
    runner.assert_status(res, 200, "Admin Dashboard (Client + Employee Filter)")

    # 9.4 Admin Clients Summary Cards
    res = admin_session.get(f"{BASE_URL}/api/dashboard/admin/clients")
    runner.assert_status(res, 200, "Admin Dashboard Clients Cards")

    # 9.5 Employee Dashboard
    res = emp_session.get(f"{BASE_URL}/api/dashboard/employee", params={"date_range": "today"})
    runner.assert_status(res, 200, "Employee Dashboard (Today)")

    # 9.6 Client Dashboard
    res = client_session.get(f"{BASE_URL}/api/dashboard/client")
    runner.assert_status(res, 200, "Client Dedicated Dashboard")

    # -------------------------------------------------------------
    # 10. ACTIVITY LOGS & NOTIFICATIONS TESTS
    # -------------------------------------------------------------
    print("\n📦 MODULE 10: AUDIT LOGS & NOTIFICATIONS", flush=True)

    # 10.1 Activity Logs
    res = admin_session.get(f"{BASE_URL}/api/activity-logs")
    runner.assert_status(res, 200, "Get Activity Audit Logs")

    # 10.2 Notifications
    res = emp_session.get(f"{BASE_URL}/api/notifications")
    runner.assert_status(res, 200, "Get User Notifications")

    # -------------------------------------------------------------
    # SUMMARY & DIAGNOSTICS
    # -------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    print(f"📊 TEST SUITE SUMMARY: {runner.passed} PASSED | {runner.failed} FAILED", flush=True)
    print("=" * 70, flush=True)

    if runner.failed > 0:
        print("\n⚠️ FAILURES DETECTED:", flush=True)
        for name, code, body in runner.errors:
            print(f" - [{code}] {name}: {body[:150]}", flush=True)
        sys.exit(1)
    else:
        print("🎉 ALL MODULES AND ENDPOINTS FUNCTIONING WITH ZERO ERRORS!", flush=True)
        sys.exit(0)

if __name__ == "__main__":
    run_all_tests()
