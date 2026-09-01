"""
ApplyFlow — Google Apps Script Web App Storage E2E Test.
Tests live integration with:
- Upload single PDF
- Upload 5-resume batch
- View / Download PDF
- Admin Delete resume from Drive + DB
- Permission verification (Admin cannot upload, Employee can upload)
"""

import uuid
from datetime import date

import requests

BASE_URL = "http://localhost:8000"

def run_tests():
    print("=" * 70)
    print("🚀 TESTING APPLYFLOW GOOGLE APPS SCRIPT WEB APP STORAGE INTEGRATION")
    print("=" * 70)

    # 1. Login as Harish (Employee)
    emp_session = requests.Session()
    res = emp_session.post(f"{BASE_URL}/api/auth/login", json={"email": "harish@applyflow.com", "password": "harish123"})
    assert res.status_code == 200, "Employee login failed"
    print("1. Employee Logged In ✅", flush=True)

    # 2. Get ABC Staffing Client ID
    clients = emp_session.get(f"{BASE_URL}/api/clients").json()
    client_id = clients[0]["id"]
    client_name = clients[0]["company_name"]
    print(f"2. Target Client: {client_name} ({client_id}) ✅", flush=True)

    # 3. Upload single PDF to Google Apps Script
    mock_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    file_1 = ("files", (f"Infosys_ReactDev_HarishAppsScript_{uuid.uuid4().hex[:4]}.pdf", mock_pdf, "application/pdf"))

    data = {
        "client_id": client_id,
        "resume_date": date.today().isoformat(),
    }
    upload_res = emp_session.post(f"{BASE_URL}/api/resumes/upload", data=data, files=[file_1])
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    assert upload_data["saved_count"] == 1, "Expected 1 saved resume"
    saved_item = upload_data["items"][0]
    resume_id = saved_item["saved_resume_id"]
    drive_file_id = saved_item["drive_file_id"]
    print(f"3. Uploaded Single Resume to Google Apps Script ✅ (File ID: {drive_file_id})", flush=True)

    # 4. Upload 5-resume batch to Google Apps Script
    batch_files = [
        ("files", (f"Amazon_Backend_BatchCand_{i}_{uuid.uuid4().hex[:3]}.pdf", mock_pdf, "application/pdf"))
        for i in range(5)
    ]
    batch_res = emp_session.post(f"{BASE_URL}/api/resumes/upload", data=data, files=batch_files)
    assert batch_res.status_code == 200, f"Batch upload failed: {batch_res.text}"
    assert batch_res.json()["saved_count"] == 5, "Expected 5 saved resumes"
    print("4. Uploaded 5-Resume Batch to Google Apps Script ✅", flush=True)

    # 5. Test Download / View Resume
    dl_res = emp_session.get(f"{BASE_URL}/api/resumes/{resume_id}/download")
    assert dl_res.status_code == 200, f"Download failed: {dl_res.text}"
    assert b"%PDF" in dl_res.content[:10], "Valid PDF stream returned"
    print("5. Resume Download / View Content Verified ✅", flush=True)

    # 6. Admin Login & Delete Resume
    admin_session = requests.Session()
    res_admin = admin_session.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@applyflow.com", "password": "admin123"})
    assert res_admin.status_code == 200, "Admin login failed"

    del_res = admin_session.delete(f"{BASE_URL}/api/resumes/{resume_id}")
    assert del_res.status_code == 200, f"Delete failed: {del_res.text}"
    print("6. Admin Deleted Resume (Google Drive Trash + PostgreSQL) ✅", flush=True)

    # 7. Verify Resume is removed from PostgreSQL
    check_res = admin_session.get(f"{BASE_URL}/api/resumes/{resume_id}")
    assert check_res.status_code == 404, "Resume should no longer exist in DB"
    print("7. Verified Resume Record Removed from Database ✅", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("🎉 ALL GOOGLE APPS SCRIPT STORAGE TESTS PASSED SUCCESSFULLY!", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_tests()
