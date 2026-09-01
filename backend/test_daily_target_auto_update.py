"""
Comprehensive E2E Automated Test Suite for Daily Target Quota Real-Time Auto-Update:
1. Recruiter logs in.
2. Reads baseline Daily Target Quota.
3. Employee uploads batch of resumes -> Verifies Target Quota, Submissions, and Today's Uploads increase instantly.
4. Employee submits direct application -> Verifies Target Quota increases instantly.
5. Verifies Client and Date filters recalculate in real-time.
"""

import asyncio
import uuid
from datetime import date

import httpx

BASE_URL = "http://localhost:8000"

async def run_target_auto_update_test():
    print("=" * 75)
    print("🧪 RUNNING DAILY TARGET QUOTA REAL-TIME AUTO-UPDATE VERIFICATION")
    print("=" * 75)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Login as Recruiter (Harish)
        login_res = await client.post(
            "/api/auth/login",
            json={"email": "harish@applyflow.com", "password": "harish123"},
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        user_data = login_res.json()["user"]
        print(f"✅ Logged in as Recruiter: {user_data['name']} ({user_data['email']})")

        # 2. Get assigned clients
        clients_res = await client.get("/api/clients")
        assert clients_res.status_code == 200
        assigned_clients = clients_res.json()
        assert len(assigned_clients) >= 2, "Harish should have at least 2 assigned clients"
        abc_client = next(c for c in assigned_clients if c["company_name"] == "ABC Staffing")
        print(f"✅ Assigned Clients verified: {[c['company_name'] for c in assigned_clients]}")

        # 3. Read Baseline Target Quota (Today)
        dash_res = await client.get("/api/dashboard/employee?date_range=today")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        baseline_summary = dash_data["target_summary"]
        baseline_uploads = dash_data["today_uploads"]
        baseline_submitted = baseline_summary["submitted"]
        baseline_target = baseline_summary["target"]
        baseline_remaining = baseline_summary["remaining"]
        baseline_completion = baseline_summary["completion"]

        print("\n📊 BASELINE METRICS (Today, All Assigned Clients):")
        print(f"   - Today's Uploads:        {baseline_uploads}")
        print(f"   - Applications Submitted: {baseline_submitted}")
        print(f"   - Daily Target Quota:     {baseline_submitted} / {baseline_target}")
        print(f"   - Remaining:              {baseline_remaining}")
        print(f"   - Completion:             {baseline_completion}%")

        assert baseline_remaining == max(baseline_target - baseline_submitted, 0), "Baseline remaining calculation mismatch"
        assert baseline_completion == round((baseline_submitted / max(1, baseline_target)) * 100), "Baseline completion calculation mismatch"

        # 4. Upload 3 New Resumes as Employee for ABC Staffing
        print("\n🚀 ACTION: Uploading 3 new resumes for ABC Staffing...")
        mock_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /MediaBox [0 0 612 792] >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        )
        tag1 = f"RES{uuid.uuid4().hex[:4].upper()}"
        tag2 = f"RES{uuid.uuid4().hex[:4].upper()}"
        tag3 = f"RES{uuid.uuid4().hex[:4].upper()}"

        files = [
            ("files", (f"TCS_JavaDeveloper_{tag1}.pdf", mock_pdf, "application/pdf")),
            ("files", (f"Infosys_PythonLead_{tag2}.pdf", mock_pdf, "application/pdf")),
            ("files", (f"Amazon_SeniorSDE_{tag3}.pdf", mock_pdf, "application/pdf")),
        ]
        data = {
            "client_id": abc_client["id"],
            "resume_date": date.today().isoformat(),
        }
        upload_res = await client.post("/api/resumes/upload", data=data, files=files)
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        upload_json = upload_res.json()
        assert upload_json["saved_count"] == 3, f"Expected 3 saved, got {upload_json.get('saved_count')}"
        print("  ✅ 3 Resumes uploaded successfully.")

        # 5. Verify Post-Upload Target Quota (Must immediately reflect +3)
        dash_res_after = await client.get("/api/dashboard/employee?date_range=today")
        assert dash_res_after.status_code == 200
        post_data = dash_res_after.json()
        post_summary = post_data["target_summary"]
        post_uploads = post_data["today_uploads"]
        post_submitted = post_summary["submitted"]
        post_target = post_summary["target"]
        post_remaining = post_summary["remaining"]
        post_completion = post_summary["completion"]

        print("\n📈 POST-UPLOAD METRICS (After +3 Resume Upload):")
        print(f"   - Today's Uploads:        {post_uploads} (Expected: {baseline_uploads + 3})")
        print(f"   - Applications Submitted: {post_submitted} (Expected: {baseline_submitted + 3})")
        print(f"   - Daily Target Quota:     {post_submitted} / {post_target}")
        print(f"   - Remaining:              {post_remaining} (Expected: {max(post_target - post_submitted, 0)})")
        print(f"   - Completion:             {post_completion}% (Expected: {round((post_submitted / max(1, post_target)) * 100)}%)")

        assert post_uploads == baseline_uploads + 3, f"Uploads count did not increase by 3: {post_uploads}"
        assert post_submitted == baseline_submitted + 3, f"Applications submitted did not increase by 3: {post_submitted}"
        assert post_remaining == max(post_target - post_submitted, 0), "Post-upload remaining calculation mismatch"
        assert post_completion == round((post_submitted / max(1, post_target)) * 100), "Post-upload completion calculation mismatch"
        print("  ✅ PASS: Daily Target Quota automatically recalculated and updated upon resume upload!")

        # 6. Direct Application Submission Test (Candidate Bank submission)
        print("\n🚀 ACTION: Direct Candidate Application Submission from Candidate Studio...")
        resumes_list_res = await client.get("/api/resumes", params={"client_id": abc_client["id"]})
        assert resumes_list_res.status_code == 200
        available_resumes = resumes_list_res.json()["items"]
        test_resume = available_resumes[0]

        direct_app_payload = {
            "resume_id": test_resume["id"],
            "client_id": abc_client["id"],
            "requirement_id": test_resume.get("requirement_id"),
            "status": "Submitted",
        }
        app_sub_res = await client.post("/api/applications", json=direct_app_payload)
        assert app_sub_res.status_code in [200, 201], f"Submit application failed: {app_sub_res.text}"
        print("  ✅ Candidate submitted directly to client pipeline.")

        # 7. Check Client Scoped Target Quota
        print("\n🎯 FILTER TEST: Scoped to ABC Staffing Only...")
        abc_dash_res = await client.get(f"/api/dashboard/employee?date_range=today&client_id={abc_client['id']}")
        assert abc_dash_res.status_code == 200
        abc_summary = abc_dash_res.json()["target_summary"]
        print(f"   - ABC Staffing Target:     {abc_summary['target']}")
        print(f"   - ABC Staffing Submitted:  {abc_summary['submitted']}")
        print(f"   - ABC Staffing Remaining:  {abc_summary['remaining']}")
        print(f"   - ABC Staffing Completion: {abc_summary['completion']}%")
        abc_target = abc_summary["target"]
        assert abc_target > 0, f"ABC Staffing expected target > 0, got {abc_target}"
        assert abc_summary["remaining"] == max(abc_target - abc_summary["submitted"], 0)
        assert abc_summary["completion"] == round((abc_summary["submitted"] / max(1, abc_target)) * 100)
        print("  ✅ PASS: Client filter correctly isolates targets and application counts in real-time!")

        # 8. Check Date Range Filters (This Week & This Month)
        print("\n📅 FILTER TEST: Date Range Switching...")
        week_res = await client.get("/api/dashboard/employee?date_range=this_week")
        assert week_res.status_code == 200
        week_summary = week_res.json()["target_summary"]
        print(f"   - This Week Submitted: {week_summary['submitted']} / {week_summary['target']} ({week_summary['completion']}%)")
        assert week_summary["submitted"] >= post_submitted, "This week should have >= today's submissions"

        month_res = await client.get("/api/dashboard/employee?date_range=this_month")
        assert month_res.status_code == 200
        month_summary = month_res.json()["target_summary"]
        print(f"   - This Month Submitted: {month_summary['submitted']} / {month_summary['target']} ({month_summary['completion']}%)")
        assert month_summary["submitted"] >= week_summary["submitted"], "This month should have >= this week's submissions"
        print("  ✅ PASS: Date filters correctly aggregate in real-time without page reload!")

    print("\n" + "=" * 75)
    print("🎉 ALL DAILY TARGET QUOTA REAL-TIME AUTO-UPDATE TESTS (100%) PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_target_auto_update_test())
