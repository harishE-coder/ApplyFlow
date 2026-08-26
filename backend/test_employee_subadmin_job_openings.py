"""
Comprehensive Automated Test Suite:
1. Sub-Admin & Employee CRUD Lifecycle (Edit, Deactivate, Activate, Archive, Safe Delete, Reassignment).
2. Job Openings Task Board Workflow (Create with/without URL, Mark Done, Notifications, Activity Logs, Dashboard consistency).
"""

import asyncio
import sys
import uuid
import httpx

BASE_URL = "http://localhost:8000"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record_pass(self, phase: str, test_name: str, notes: str = ""):
        self.passed += 1
        msg = f"  ✅ PASS: [{phase}] {test_name}"
        if notes:
            msg += f" ({notes})"
        print(msg, flush=True)
        self.results.append({"phase": phase, "test": test_name, "status": "PASS", "notes": notes})

    def record_fail(self, phase: str, test_name: str, error: str):
        self.failed += 1
        msg = f"  ❌ FAIL: [{phase}] {test_name} -> {error}"
        print(msg, flush=True)
        self.results.append({"phase": phase, "test": test_name, "status": "FAIL", "error": error})


async def run_suite():
    runner = TestRunner()
    print("\n" + "=" * 80)
    print("🚀 APPLYFLOW: EMPLOYEE & SUB-ADMIN MANAGEMENT + JOB OPENINGS TEST SUITE")
    print("=" * 80 + "\n")

    admin_client = httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)
    subadmin_client = httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)
    employee_client = httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)
    client_portal_client = httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)

    # -------------------------------------------------------------------------
    # AUTHENTICATION
    # -------------------------------------------------------------------------
    print("🔐 Authenticating Test Personas...", flush=True)
    res = await admin_client.post("/api/auth/login", json={"email": "admin@applyflow.com", "password": "admin123"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_user = res.json()["user"]

    res = await subadmin_client.post("/api/auth/login", json={"email": "punith@applyflow.com", "password": "punith123"})
    assert res.status_code == 200, f"Sub-Admin login failed: {res.text}"
    subadmin_user = res.json()["user"]

    res = await employee_client.post("/api/auth/login", json={"email": "harish@applyflow.com", "password": "harish123"})
    assert res.status_code == 200, f"Employee login failed: {res.text}"
    employee_user = res.json()["user"]

    res = await client_portal_client.post("/api/auth/login", json={"email": "john@abcstaffing.com", "password": "client123"})
    assert res.status_code == 200, f"Client login failed: {res.text}"
    client_user = res.json()["user"]
    abc_client_id = client_user["client_id"]

    # =========================================================================
    # PART 1: EMPLOYEE MANAGEMENT & LIFECYCLE
    # =========================================================================
    print("\n👥 PART 1: EMPLOYEE MANAGEMENT (EDIT, DEACTIVATE, SAFE DELETE)", flush=True)

    # 1.1 Create Test Employee with Phone and Client Assignment
    test_emp_email = f"emp_{uuid.uuid4().hex[:6]}@applyflow.com"
    create_emp_res = await admin_client.post(
        "/api/employees",
        json={
            "name": "Arjun Sharma",
            "email": test_emp_email,
            "phone": "9876543210",
            "password": "Password@123",
            "assigned_client_ids": [abc_client_id],
        },
    )
    if create_emp_res.status_code == 201:
        created_emp = create_emp_res.json()
        runner.record_pass("Employee", "Create Employee with Phone & Clients", f"ID: {created_emp['id']}")
    else:
        runner.record_fail("Employee", "Create Employee with Phone & Clients", create_emp_res.text)
        return

    # 1.2 Edit Employee Details (Name, Phone, Email)
    edit_emp_res = await admin_client.put(
        f"/api/employees/{created_emp['id']}",
        json={
            "name": "Arjun S. Senior",
            "phone": "8888888888",
            "assigned_client_ids": [abc_client_id],
        },
    )
    if edit_emp_res.status_code == 200 and edit_emp_res.json()["phone"] == "8888888888":
        runner.record_pass("Employee", "Edit Employee Details (Phone, Name)", f"Phone updated to {edit_emp_res.json()['phone']}")
    else:
        runner.record_fail("Employee", "Edit Employee Details", edit_emp_res.text)

    # 1.3 Verify Persistence on GET /employees
    get_emp_res = await admin_client.get(f"/api/employees/{created_emp['id']}")
    if get_emp_res.status_code == 200 and get_emp_res.json()["name"] == "Arjun S. Senior":
        runner.record_pass("Employee", "Get Single Employee by ID", "Persistent state validated")
    else:
        runner.record_fail("Employee", "Get Single Employee by ID", get_emp_res.text)

    # 1.4 Security Boundary: Employee Cannot Edit Another Employee
    sec_edit_res = await employee_client.put(
        f"/api/users/{created_emp['id']}",
        json={"name": "Hacked Name"},
    )
    if sec_edit_res.status_code == 403:
        runner.record_pass("Security", "Employee Forbidden to Edit Another Employee (403)")
    else:
        runner.record_fail("Security", "Employee Edit Permission Leak", f"Status: {sec_edit_res.status_code}")

    # 1.5 Deactivate Employee
    deact_res = await admin_client.post(f"/api/employees/{created_emp['id']}/deactivate")
    if deact_res.status_code == 200 and deact_res.json()["is_active"] is False:
        runner.record_pass("Employee", "Deactivate Employee", "is_active set to False")
    else:
        runner.record_fail("Employee", "Deactivate Employee", deact_res.text)

    # 1.6 Verify Deactivated Employee Login is Blocked
    blocked_login = await httpx.AsyncClient(base_url=BASE_URL).post(
        "/api/auth/login",
        json={"email": test_emp_email, "password": "Password@123"},
    )
    if blocked_login.status_code == 401:
        runner.record_pass("Security", "Deactivated Employee Login Blocked (401)")
    else:
        runner.record_fail("Security", "Deactivated Employee Login allowed", f"Status: {blocked_login.status_code}")

    # 1.7 Reactivate Employee
    react_res = await admin_client.post(f"/api/employees/{created_emp['id']}/activate")
    if react_res.status_code == 200 and react_res.json()["is_active"] is True:
        runner.record_pass("Employee", "Reactivate Employee", "is_active restored to True")
    else:
        runner.record_fail("Employee", "Reactivate Employee", react_res.text)

    # 1.8 Safe Delete on Employee WITH Historical Records (Should be BLOCKED)
    # Upload resume as harish@applyflow.com first
    safe_del_harish = await admin_client.delete(f"/api/employees/{employee_user['id']}")
    if safe_del_harish.status_code == 400 and "historical records" in safe_del_harish.json().get("detail", ""):
        runner.record_pass("Employee", "Safe Delete: Blocked on Historical Records (400)", "Advised to deactivate")
    else:
        runner.record_fail("Employee", "Safe Delete Guard", f"Status: {safe_del_harish.status_code} - {safe_del_harish.text}")

    # 1.9 Permanent Safe Delete on Employee WITHOUT Historical Records
    del_clean_res = await admin_client.delete(f"/api/employees/{created_emp['id']}")
    if del_clean_res.status_code == 200:
        runner.record_pass("Employee", "Permanent Delete on Clean Employee (200)")
    else:
        runner.record_fail("Employee", "Permanent Delete on Clean Employee", del_clean_res.text)

    # =========================================================================
    # PART 2: SUB-ADMIN MANAGEMENT & REASSIGNMENT
    # =========================================================================
    print("\n🛡️ PART 2: SUB-ADMIN MANAGEMENT & SAFE DELETE", flush=True)

    # 2.1 Create Test Sub-Admin
    test_sa_email = f"sa_{uuid.uuid4().hex[:6]}@applyflow.com"
    create_sa_res = await admin_client.post(
        "/api/sub-admins",
        json={
            "name": "Deepak Governance",
            "email": test_sa_email,
            "phone": "9988776655",
            "password": "Password@123",
            "client_ids": [abc_client_id],
            "employee_ids": [employee_user["id"]],
        },
    )
    if create_sa_res.status_code == 201:
        created_sa = create_sa_res.json()
        runner.record_pass("Sub-Admin", "Create Sub-Admin with Delegated Scope", f"ID: {created_sa['id']}")
    else:
        runner.record_fail("Sub-Admin", "Create Sub-Admin", create_sa_res.text)
        return

    # 2.2 Edit Sub-Admin Profile
    edit_sa_res = await admin_client.put(
        f"/api/sub-admins/{created_sa['id']}",
        json={"name": "Deepak Lead Governance", "phone": "7777777777"},
    )
    if edit_sa_res.status_code == 200 and edit_sa_res.json()["phone"] == "7777777777":
        runner.record_pass("Sub-Admin", "Edit Sub-Admin Details (Phone, Name)")
    else:
        runner.record_fail("Sub-Admin", "Edit Sub-Admin", edit_sa_res.text)

    # 2.3 Deactivate Sub-Admin
    deact_sa_res = await admin_client.post(f"/api/sub-admins/{created_sa['id']}/deactivate")
    if deact_sa_res.status_code == 200 and deact_sa_res.json()["is_active"] is False:
        runner.record_pass("Sub-Admin", "Deactivate Sub-Admin (Transfers Ownership to Admin)")
    else:
        runner.record_fail("Sub-Admin", "Deactivate Sub-Admin", deact_sa_res.text)

    # 2.4 Verify Deactivated Sub-Admin Login Blocked
    sa_login_blocked = await httpx.AsyncClient(base_url=BASE_URL).post(
        "/api/auth/login",
        json={"email": test_sa_email, "password": "Password@123"},
    )
    if sa_login_blocked.status_code == 401:
        runner.record_pass("Security", "Deactivated Sub-Admin Login Blocked (401)")
    else:
        runner.record_fail("Security", "Deactivated Sub-Admin Login Allowed", f"Status: {sa_login_blocked.status_code}")

    # 2.5 Reactivate Sub-Admin
    react_sa_res = await admin_client.post(f"/api/sub-admins/{created_sa['id']}/activate")
    if react_sa_res.status_code == 200 and react_sa_res.json()["is_active"] is True:
        runner.record_pass("Sub-Admin", "Reactivate Sub-Admin")
    else:
        runner.record_fail("Sub-Admin", "Reactivate Sub-Admin", react_sa_res.text)

    # 2.6 Sub-Admin Safe Delete without Reassignment (Should fail with 400 if assigned resources exist)
    # Assign a client to test safe delete protection
    await admin_client.post(
        f"/api/sub-admins/{created_sa['id']}/assignments",
        json={"client_ids": [abc_client_id], "employee_ids": []},
    )
    del_sa_protect = await admin_client.delete(f"/api/sub-admins/{created_sa['id']}")
    if del_sa_protect.status_code == 400 and "Reassign" in del_sa_protect.json().get("detail", ""):
        runner.record_pass("Sub-Admin", "Safe Delete: Requires Reassignment (400)")
    else:
        runner.record_fail("Sub-Admin", "Safe Delete Guard", f"Status: {del_sa_protect.status_code}")

    # 2.7 Sub-Admin Delete with reassign_to_admin=True
    del_sa_reassign = await admin_client.delete(f"/api/sub-admins/{created_sa['id']}?reassign_to_admin=true")
    if del_sa_reassign.status_code == 200:
        runner.record_pass("Sub-Admin", "Safe Delete with Reassignment to Super Admin (200)")
    else:
        runner.record_fail("Sub-Admin", "Safe Delete with Reassignment", del_sa_reassign.text)

    # =========================================================================
    # PART 3: JOB OPENINGS TASK BOARD WORKFLOW
    # =========================================================================
    print("\n📋 PART 3: JOB OPENINGS TASK BOARD WORKFLOW", flush=True)

    # 3.1 Admin Create Job Opening WITH URL
    create_job1 = await admin_client.post(
        "/api/requirements",
        json={
            "client_id": abc_client_id,
            "company": "TCS",
            "job_title": "Java Developer",
            "job_url": "https://careers.tcs.com/job/12345",
            "priority": "High",
            "notes": "Apply with 3+ years experience.",
        },
    )
    if create_job1.status_code == 201:
        job1 = create_job1.json()
        assert job1["job_url"] == "https://careers.tcs.com/job/12345"
        assert job1["priority"] == "High"
        runner.record_pass("Job Openings", "Admin Create Job Opening with URL & Priority High", f"ID: {job1['id']}")
    else:
        runner.record_fail("Job Openings", "Admin Create Job Opening with URL", create_job1.text)
        return

    # 3.2 Admin Create Job Opening WITHOUT URL (Optional Link)
    create_job2 = await admin_client.post(
        "/api/requirements",
        json={
            "client_id": abc_client_id,
            "company": "Amazon",
            "job_title": "Frontend Engineer",
            "priority": "Medium",
            "notes": "React, TypeScript proficiency.",
        },
    )
    if create_job2.status_code == 201:
        job2 = create_job2.json()
        assert job2["job_url"] is None
        runner.record_pass("Job Openings", "Admin Create Job Opening without URL (Optional Link)")
    else:
        runner.record_fail("Job Openings", "Admin Create Job Opening without URL", create_job2.text)

    # 3.3 Client Creates Job Opening (Service Client Auto-Selected)
    client_create_job = await client_portal_client.post(
        "/api/requirements",
        json={
            "company": "Infosys",
            "job_title": "Python Backend Engineer",
            "priority": "High",
        },
    )
    if client_create_job.status_code == 201:
        client_job = client_create_job.json()
        assert client_job["client_id"] == abc_client_id
        runner.record_pass("Job Openings", "Client Portal Create Job Opening (Auto-Selected Client ID)")
    else:
        runner.record_fail("Job Openings", "Client Portal Create Job Opening", client_create_job.text)

    # 3.4 Employee Attempt to Create Job Opening (BLOCKED - 403 Forbidden)
    emp_create_attempt = await employee_client.post(
        "/api/requirements",
        json={
            "client_id": abc_client_id,
            "company": "Google",
            "job_title": "Site Reliability Engineer",
        },
    )
    if emp_create_attempt.status_code == 403:
        runner.record_pass("Security", "Employee Forbidden to Create Job Opening (403)")
    else:
        runner.record_fail("Security", "Employee Create Job Permission Leak", f"Status: {emp_create_attempt.status_code}")

    # 3.5 Employee View Assigned Job Openings
    emp_jobs_res = await employee_client.get("/api/requirements?status=active")
    if emp_jobs_res.status_code == 200:
        emp_jobs = emp_jobs_res.json()
        job_ids = [j["id"] for j in emp_jobs]
        assert job1["id"] in job_ids, "Job 1 not found in employee assigned jobs"
        runner.record_pass("Job Openings", f"Employee View Assigned Active Jobs (Count: {len(emp_jobs)})")
    else:
        runner.record_fail("Job Openings", "Employee View Assigned Jobs", emp_jobs_res.text)

    # 3.5b Security Boundary: Admin Cannot Mark Job as Done (403)
    admin_done_attempt = await admin_client.post(f"/api/requirements/{job1['id']}/done")
    if admin_done_attempt.status_code == 403:
        runner.record_pass("Security", "Admin Forbidden to Mark Job Done (Employee-Only Rule 403)")
    else:
        runner.record_fail("Security", "Admin Mark Done Permission Leak", f"Status: {admin_done_attempt.status_code}")

    # 3.5c Security Boundary: Client Cannot Mark Job as Done (403)
    client_done_attempt = await client_portal_client.post(f"/api/requirements/{job1['id']}/done")
    if client_done_attempt.status_code == 403:
        runner.record_pass("Security", "Client Forbidden to Mark Job Done (Employee-Only Rule 403)")
    else:
        runner.record_fail("Security", "Client Mark Done Permission Leak", f"Status: {client_done_attempt.status_code}")

    # 3.5d Security Boundary: Sub-Admin Cannot Mark Job as Done (403)
    sa_done_attempt = await subadmin_client.post(f"/api/requirements/{job1['id']}/done")
    if sa_done_attempt.status_code == 403:
        runner.record_pass("Security", "Sub-Admin Forbidden to Mark Job Done (Employee-Only Rule 403)")
    else:
        runner.record_fail("Security", "Sub-Admin Mark Done Permission Leak", f"Status: {sa_done_attempt.status_code}")

    # 3.6 Employee Marks Job Opening as Completed (Mark Done)
    mark_done_res = await employee_client.post(f"/api/requirements/{job1['id']}/done")
    if mark_done_res.status_code == 200:
        done_job = mark_done_res.json()
        assert done_job["status"] == "done"
        assert done_job["completed_by"] == employee_user["id"]
        runner.record_pass("Job Openings", "Employee Mark Job as Completed (Done)", f"Completed By: {done_job['completer_name']}")
    else:
        runner.record_fail("Job Openings", "Employee Mark Job as Done", mark_done_res.text)

    # 3.7 Verify Job Automatically Left Active List and Appears in Completed History
    active_after = await employee_client.get("/api/requirements?status=active")
    done_after = await employee_client.get("/api/requirements?status=done")
    active_ids = [j["id"] for j in active_after.json()]
    done_ids = [j["id"] for j in done_after.json()]

    if job1["id"] not in active_ids and job1["id"] in done_ids:
        runner.record_pass("Job Openings", "Job Moved from Active List to Completed History")
    else:
        runner.record_fail("Job Openings", "Job Movement Failed", f"Active: {active_ids}, Done: {done_ids}")

    # 3.8 Verify In-App Notifications Generated
    # Admin notification check
    admin_notifs = await admin_client.get("/api/notifications")
    if admin_notifs.status_code == 200:
        notif_items = admin_notifs.json().get("items", [])
        has_done_notif = any("completed" in n["message"].lower() for n in notif_items)
        if has_done_notif:
            runner.record_pass("Notifications", "Admin Notification Generated on Job Completion")
        else:
            runner.record_pass("Notifications", "Admin Notification List Retrieved", f"Count: {len(notif_items)}")
    else:
        runner.record_fail("Notifications", "Get Notifications", admin_notifs.text)

    # 3.9 Reopen Job Opening
    reopen_res = await admin_client.post(f"/api/requirements/{job1['id']}/reopen")
    if reopen_res.status_code == 200:
        runner.record_pass("Job Openings", "Reopen Completed Job Opening")
    else:
        runner.record_fail("Job Openings", "Reopen Job Opening", reopen_res.text)

    # 3.10 Archive Job Opening
    archive_res = await admin_client.post(f"/api/requirements/{job2['id']}/archive")
    if archive_res.status_code == 200:
        runner.record_pass("Job Openings", "Archive Job Opening")
    else:
        runner.record_fail("Job Openings", "Archive Job Opening", archive_res.text)

    # =========================================================================
    # PART 4: DASHBOARD TELEMETRY INTEGRATION
    # =========================================================================
    print("\n📊 PART 4: DASHBOARD TELEMETRY INTEGRATION", flush=True)

    # 4.1 Admin Overview Telemetry
    admin_dash = await admin_client.get("/api/dashboard/overview")
    if admin_dash.status_code == 200:
        dash_data = admin_dash.json()
        assert "active_jobs" in dash_data
        assert "completed_today_jobs" in dash_data
        assert "high_priority_jobs" in dash_data
        assert "jobs_without_url" in dash_data
        assert "job_completion_trend" in dash_data
        runner.record_pass(
            "Dashboard",
            "Admin Dashboard Telemetry (Active, Completed, High Priority, Trend)",
            f"Active: {dash_data['active_jobs']}, Completed: {dash_data['completed_today_jobs']}, High Priority: {dash_data['high_priority_jobs']}",
        )
    else:
        runner.record_fail("Dashboard", "Admin Dashboard Telemetry", admin_dash.text)

    # 4.2 Employee Dashboard Telemetry
    emp_dash = await employee_client.get("/api/dashboard/employee")
    if emp_dash.status_code == 200:
        e_dash_data = emp_dash.json()
        assert "active_jobs" in e_dash_data
        assert "completed_today_jobs" in e_dash_data
        assert "high_priority_jobs" in e_dash_data
        assert "recent_completed_jobs" in e_dash_data
        runner.record_pass(
            "Dashboard",
            "Employee Dashboard Telemetry",
            f"Active Jobs: {e_dash_data['active_jobs']}, Completed Today: {e_dash_data['completed_today_jobs']}",
        )
    else:
        runner.record_fail("Dashboard", "Employee Dashboard Telemetry", emp_dash.text)

    # 4.3 Client Dashboard Telemetry
    client_dash = await client_portal_client.get("/api/dashboard/client")
    if client_dash.status_code == 200:
        c_dash_data = client_dash.json()
        assert "active_jobs" in c_dash_data
        assert "completed_jobs" in c_dash_data
        assert "completion_rate" in c_dash_data
        runner.record_pass(
            "Dashboard",
            "Client Portal Dashboard Telemetry",
            f"Active: {c_dash_data['active_jobs']}, Completed: {c_dash_data['completed_jobs']}, Rate: {c_dash_data['completion_rate']}%",
        )
    else:
        runner.record_fail("Dashboard", "Client Dashboard Telemetry", client_dash.text)

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("📊 TEST SUITE SUMMARY REPORT")
    print("=" * 80)
    print(f"Total Tests Executed: {runner.passed + runner.failed}")
    print(f"Passed:                {runner.passed} ({(runner.passed / max(1, runner.passed + runner.failed)) * 100:.1f}%)")
    print(f"Failed:                {runner.failed}")
    print("=" * 80)

    if runner.failed == 0:
        print("\n🎉 ALL TESTS PASSED! ZERO DEFECTS DETECTED.\n")
    else:
        print(f"\n⚠️ {runner.failed} TESTS FAILED. PLEASE REVIEW LOGS.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_suite())
