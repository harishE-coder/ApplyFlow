"""
Unit Test for ApplyFlow Strict ServiceClient Filename Verification
"""
from app.modules.resumes.parser import parse_resume_filename

def test_service_client_verification_rules():
    print("\n--- Test 1: Teksystems with matching filename ---")
    res1 = parse_resume_filename("Teksystems_Google_Data Analyst.pdf", selected_client_name="Teksystems")
    print("Result 1:", res1)
    assert res1["status"] == "valid"
    assert res1["client_match"] is True
    assert res1["service_client"] == "Teksystems"
    assert res1["company"] == "Google"
    assert res1["role"] == "Data Analyst"
    print("✅ Verified!")

    print("\n--- Test 2: Infosys with matching filename ---")
    res2 = parse_resume_filename("Infosys_Microsoft_Java Developer.pdf", selected_client_name="Infosys")
    print("Result 2:", res2)
    assert res2["status"] == "valid"
    assert res2["client_match"] is True
    assert res2["service_client"] == "Infosys"
    assert res2["company"] == "Microsoft"
    assert res2["role"] == "Java Developer"
    print("✅ Verified!")

    print("\n--- Test 3: Teksystems selected with Infosys filename (ServiceClient Mismatch) ---")
    res3 = parse_resume_filename("Infosys_Amazon_QA Engineer.pdf", selected_client_name="Teksystems")
    print("Result 3:", res3)
    assert res3["status"] == "needs_review"
    assert res3["client_match"] is False
    assert res3["error"] == "ServiceClient Mismatch"
    print("✅ Verified Mismatch detection!")

    print("\n--- Test 4: Teksystems selected with Suresh_resume (2).pdf (Natural Candidate Resume) ---")
    res4 = parse_resume_filename("Suresh_resume (2).pdf", selected_client_name="Teksystems")
    print("Result 4:", res4)
    assert res4["status"] == "valid"
    assert res4["client_match"] is True
    assert res4["service_client"] == "Teksystems"
    assert res4["candidate_name"] == "Suresh"
    print("✅ Verified Natural Resume auto-inheritance!")

    print("\n--- Test 5: Teksystems selected with Suresh_resume.pdf (Natural Candidate Resume) ---")
    res5 = parse_resume_filename("Suresh_resume.pdf", selected_client_name="Teksystems")
    print("Result 5:", res5)
    assert res5["status"] == "valid"
    assert res5["client_match"] is True
    assert res5["service_client"] == "Teksystems"
    assert res5["candidate_name"] == "Suresh"
    print("✅ Verified Natural Resume auto-inheritance!")

    print("\n--- Test 6: No client selected with Suresh_resume.pdf ---")
    res6 = parse_resume_filename("Suresh_resume.pdf", selected_client_name=None)
    print("Result 6:", res6)
    assert res6["status"] == "needs_review"
    assert res6["client_match"] is False
    assert res6["error"] == "Cannot detect ServiceClient from filename"
    print("✅ Verified Missing Client prompts review!")

    print("\n=======================================================")
    print("🎉 ALL STRICT SERVICECLIENT VERIFICATION TESTS PASSED 100%!")
    print("=======================================================\n")

if __name__ == "__main__":
    test_service_client_verification_rules()
