"""
Automated Test Suite for ApplyFlow Locked Filename Standard & Parser:
ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf
"""

import asyncio
import uuid

import httpx
from app.modules.resumes.parser import parse_resume_filename

BASE_URL = "http://localhost:8000"


def run_unit_parser_tests():
    print("\n" + "=" * 80)
    print("🧪 1. UNIT TESTS: APPLYFLOW RESUME FILENAME PARSER")
    print("=" * 80)

    # Test 1: ABCStaffing_TCS_JavaDeveloper_RES101.pdf
    res1 = parse_resume_filename("ABCStaffing_TCS_JavaDeveloper_RES101.pdf", selected_client_name="ABC Staffing")
    print("\n[Test 1] ABCStaffing_TCS_JavaDeveloper_RES101.pdf:")
    print(f"  Parsed: {res1}")
    assert res1["success"] is True
    assert res1["service_client"] == "ABC Staffing"
    assert res1["company"] == "TCS"
    assert res1["role"] == "Java Developer"
    assert res1["resume_identifier"] == "RES101"
    assert res1["resume_id_tag"] == "RES101"
    assert res1["client_match"] is True
    print("  ✅ PASS: Parsed Client=ABC Staffing, Company=TCS, Role=Java Developer, Resume ID=RES101")

    # Test 2: TalentHub_Amazon_SDEII_RES205.pdf
    res2 = parse_resume_filename("TalentHub_Amazon_SDEII_RES205.pdf", selected_client_name="Talent Hub")
    print("\n[Test 2] TalentHub_Amazon_SDEII_RES205.pdf:")
    print(f"  Parsed: {res2}")
    assert res2["success"] is True
    assert res2["service_client"] == "Talent Hub"
    assert res2["company"] == "Amazon"
    assert res2["role"] == "SDE II"
    assert res2["resume_identifier"] == "RES205"
    assert res2["resume_id_tag"] == "RES205"
    assert res2["client_match"] is True
    print("  ✅ PASS: Parsed Client=Talent Hub, Company=Amazon, Role=SDE II, Resume ID=RES205")

    # Test 3: NextHire_Infosys_INF-PY-02_RahulKumar.pdf
    res3 = parse_resume_filename("NextHire_Infosys_INF-PY-02_RahulKumar.pdf", selected_client_name="NextHire")
    print("\n[Test 3] NextHire_Infosys_INF-PY-02_RahulKumar.pdf:")
    print(f"  Parsed: {res3}")
    assert res3["success"] is True
    assert res3["service_client"] == "NextHire"
    assert res3["company"] == "Infosys"
    assert res3["role"] == "INF-PY-02"
    assert res3["resume_identifier"] == "RahulKumar"
    assert res3["client_match"] is True
    print("  ✅ PASS: Parsed Client=NextHire, Company=Infosys, Role=INF-PY-02, Resume ID=RahulKumar")

    # Test 4: Invalid Filename - TCS_JavaDeveloper.pdf (2 segments)
    res_inv1 = parse_resume_filename("TCS_JavaDeveloper.pdf", selected_client_name="ABC Staffing")
    print("\n[Test 4] Invalid - TCS_JavaDeveloper.pdf:")
    print(f"  Parsed: {res_inv1}")
    assert res_inv1["success"] is False
    assert "Invalid filename format" in res_inv1["error"]
    print("  ✅ PASS: Correctly rejected 2-segment filename as invalid format")

    # Test 5: Invalid Filename - ABCStaffing_TCS.pdf (2 segments)
    res_inv2 = parse_resume_filename("ABCStaffing_TCS.pdf", selected_client_name="ABC Staffing")
    print("\n[Test 5] Invalid - ABCStaffing_TCS.pdf:")
    print(f"  Parsed: {res_inv2}")
    assert res_inv2["success"] is False
    assert "Invalid filename format" in res_inv2["error"]
    print("  ✅ PASS: Correctly rejected 2-segment filename as invalid format")

    # Test 6: Invalid Filename - Amazon.pdf (1 segment)
    res_inv3 = parse_resume_filename("Amazon.pdf", selected_client_name="ABC Staffing")
    print("\n[Test 6] Invalid - Amazon.pdf:")
    print(f"  Parsed: {res_inv3}")
    assert res_inv3["success"] is False
    assert "Invalid filename format" in res_inv3["error"]
    print("  ✅ PASS: Correctly rejected 1-segment filename as invalid format")

    # Test 7: Client Mismatch - Selected ABC Staffing, Filename TalentHub_TCS_JavaDeveloper_RES101.pdf
    res_mismatch = parse_resume_filename("TalentHub_TCS_JavaDeveloper_RES101.pdf", selected_client_name="ABC Staffing")
    print("\n[Test 7] Client Mismatch - TalentHub_TCS_JavaDeveloper_RES101.pdf with selected ABC Staffing:")
    print(f"  Parsed: {res_mismatch}")
    assert res_mismatch["success"] is False
    assert res_mismatch["client_match"] is False
    assert "does not match selected Service Client" in res_mismatch["error"]
    print("  ✅ PASS: Correctly flagged client mismatch and blocked validation")

    print("\n" + "=" * 80)
    print("🎉 ALL 7 UNIT TESTS PASSED!")
    print("=" * 80 + "\n")


async def run_e2e_api_tests():
    print("=" * 80)
    print("🚀 2. END-TO-END API INTEGRATION TESTS: UPLOAD & DUPLICATE CHECKS")
    print("=" * 80)

    client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    # 1. Login as Employee
    login_res = await client.post("/api/auth/login", json={"email": "qa_recruiter@applyflow.com", "password": "Recruiter@123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    _user_info = login_res.json()["user"]

    # 2. Get ABC Staffing Client
    clients_res = await client.get("/api/clients")
    assert clients_res.status_code == 200
    clients = clients_res.json()
    abc_client = next((c for c in clients if "ABC Staffing" in c["company_name"]), clients[0])

    mock_pdf = b"%PDF-1.4 Mock PDF Content For Parser Verification"

    # 3. Upload Valid 4-Segment Filename: ABCStaffing_TCS_JavaDeveloper_RES101.pdf
    tag = f"RES{uuid.uuid4().hex[:4].upper()}"
    valid_fname = f"ABCStaffing_TCS_JavaDeveloper_{tag}.pdf"
    up_res = await client.post(
        "/api/resumes/upload",
        data={"client_id": abc_client["id"]},
        files=[("files", (valid_fname, mock_pdf, "application/pdf"))],
    )
    assert up_res.status_code == 200, f"Upload failed: {up_res.text}"
    up_data = up_res.json()
    assert up_data["saved_count"] == 1
    item = up_data["items"][0]
    assert item["status"] == "saved"
    assert item["company"] == "TCS"
    assert item["role"] == "Java Developer"
    assert item["resume_id_tag"] == tag
    print(f"  ✅ PASS: Uploaded valid 4-segment resume ({valid_fname}) -> Saved to DB")

    # 4. Check Duplicate on re-upload
    dup_res = await client.post(
        "/api/resumes/check-duplicates",
        json={
            "client_id": abc_client["id"],
            "items": [
                {
                    "filename": valid_fname,
                    "company": "TCS",
                    "candidate_name": f"Candidate {tag}",
                    "resume_id_tag": tag,
                }
            ],
        },
    )
    assert dup_res.status_code == 200
    dup_data = dup_res.json()
    assert dup_data["results"][0]["is_duplicate"] is True
    print(f"  ✅ PASS: Duplicate detection verified for ({valid_fname})")

    # 5. Upload Client Mismatch Filename -> Flags Needs Review
    mismatch_fname = f"NextHire_Amazon_SDEII_RES{uuid.uuid4().hex[:4].upper()}.pdf"
    up_mismatch = await client.post(
        "/api/resumes/upload",
        data={"client_id": abc_client["id"]},
        files=[("files", (mismatch_fname, mock_pdf, "application/pdf"))],
    )
    assert up_mismatch.status_code == 200
    mismatch_data = up_mismatch.json()
    assert mismatch_data["needs_review_count"] == 1
    assert mismatch_data["items"][0]["status"] == "needs_review"
    assert "does not match selected Service Client" in mismatch_data["items"][0]["message"]
    print(f"  ✅ PASS: Client mismatch filename ({mismatch_fname}) flagged for review and blocked from auto-saving")

    print("\n" + "=" * 80)
    print("🎉 ALL END-TO-END INTEGRATION TESTS PASSED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_unit_parser_tests()
    asyncio.run(run_e2e_api_tests())
