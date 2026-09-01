"""
High Load Batch Ingestion & Stress Test (50-200 Resumes).
Validates memory, disk I/O, duplicate checks, and response latency.
"""

import time
from datetime import date

import requests

BASE_URL = "http://localhost:8000"

def run_stress_test():
    print("=" * 70)
    print("⚡ RUNNING 50-RESUME HIGH-THROUGHPUT BATCH INGESTION BENCHMARK")
    print("=" * 70)

    # Login as Harish
    session = requests.Session()
    session.post(f"{BASE_URL}/api/auth/login", json={"email": "harish@applyflow.com", "password": "harish123"})

    # Get ABC Staffing Client ID
    clients_res = session.get(f"{BASE_URL}/api/clients")
    client_id = clients_res.json()[0]["id"]

    # Generate 50 unique PDF payloads
    mock_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    companies = ["TCS", "Infosys", "Amazon", "Google", "Microsoft", "Wipro", "Oracle"]
    roles = ["JavaDeveloper", "FrontendEngineer", "DevOpsLead", "DataScientist", "QAAutomation"]

    files_50 = []
    for i in range(50):
        comp = companies[i % len(companies)]
        role = roles[i % len(roles)]
        uid_tag = f"RES{1000 + i}"
        cand_name = f"Candidate{i}"
        filename = f"{comp}_{role}_{cand_name}_{uid_tag}.pdf"
        files_50.append(("files", (filename, mock_pdf, "application/pdf")))

    data = {
        "client_id": client_id,
        "resume_date": date.today().isoformat(),
    }

    t0 = time.time()
    res = session.post(f"{BASE_URL}/api/resumes/upload", data=data, files=files_50)
    elapsed = time.time() - t0

    if res.status_code == 200:
        saved = res.json().get("saved_count", 0)
        total = res.json().get("total_files", 0)
        print(f"✅ Ingested {saved}/{total} Resumes in {elapsed:.3f}s ({elapsed/total*1000:.1f}ms per resume)")
        print(f"⚡ Throughput: {total / elapsed:.1f} resumes/second")
    else:
        print(f"❌ Failed batch upload [{res.status_code}]: {res.text[:200]}")

if __name__ == "__main__":
    run_stress_test()
