"""
ApplyFlow Resume Filename Parser (Strict ServiceClient Filename Verification)

Filename formats:
1. Standard 3-part: ServiceClient_HiringCompany_Role.pdf (e.g. Teksystems_Google_Data Analyst.pdf)
2. Standard 4-part: ServiceClient_HiringCompany_Role_Candidate.pdf
3. Natural resumes: Suresh_resume (2).pdf, Suresh_resume.pdf, John_Doe.pdf

Validation Rules (Employee Upload):
- If filename has structured format (ServiceClient_Company_Role):
  - ServiceClient (segment 0) is strictly compared against selected ServiceClient.
  - If mismatch -> 'ServiceClient Mismatch' (blocked).
  - If matching -> 'ServiceClient Verified' (valid).
- If filename is a natural candidate resume (e.g. Suresh_resume.pdf):
  - Automatically inherits the selected ServiceClient -> 'ServiceClient Verified' (valid).
  - If no client selected in form -> 'Cannot detect ServiceClient from filename' (needs review).
- Company and Role are purely extracted and never block upload.
"""

import re
from pathlib import Path


def _normalize_client_name(name: str | None) -> str:
    """Normalize client name for case-insensitive and whitespace-insensitive comparison."""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()


def _clean_candidate_name(raw_name: str) -> str:
    """Clean candidate name by removing noise like (1), (2), resume, cv, copy, etc."""
    if not raw_name:
        return "Candidate"
    cleaned = re.sub(r'\.pdf$', '', raw_name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\(\[\{]\d+[\)\]\}]', '', cleaned)
    cleaned = re.sub(r'\b(resume|cv|biodata|profile|curriculum|vitae)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[-_]+', ' ', cleaned)
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title() if cleaned else "Candidate"


def format_role_title(role_raw: str | None) -> str:
    """Format role names and preserve role codes."""
    if not role_raw or not role_raw.strip():
        return ""

    role_raw = role_raw.strip()

    if re.match(r'^SDE[IVX\d]*$', role_raw, re.IGNORECASE):
        match = re.match(r'^(SDE)([IVX\d]+)$', role_raw, re.IGNORECASE)
        if match:
            return f"{match.group(1).upper()} {match.group(2).upper()}"
        return role_raw.upper()

    if "-" in role_raw or bool(re.search(r'\d', role_raw) and re.search(r'[A-Za-z]', role_raw) and len(role_raw) <= 10):
        return role_raw.upper()

    if role_raw.isupper() and len(role_raw) <= 5:
        return role_raw

    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', role_raw)
    spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
    spaced = spaced.replace("_", " ").strip()
    return spaced.title()


def format_client_name(client_raw: str | None) -> str:
    """Format client names nicely from filename segment."""
    if not client_raw or not client_raw.strip():
        return ""
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', client_raw)
    spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
    return spaced.strip()


def parse_resume_filename(
    filename: str,
    selected_client_name: str | None = None,
    all_clients: list[str] | None = None,
) -> dict:
    """
    Parse resume filename with strict ServiceClient validation.
    """
    stem = Path(filename).stem.strip()
    parts = [p.strip() for p in stem.split('_') if p.strip()]

    raw_first = parts[0] if parts else ""
    norm_first = _normalize_client_name(raw_first)
    norm_selected = _normalize_client_name(selected_client_name) if selected_client_name else ""

    has_noise = any(re.search(r'\b(resume|cv|biodata)\b|[\(\[\{]\d+[\)\]\}]', p, re.IGNORECASE) for p in parts)

    service_client = selected_client_name or (format_client_name(raw_first) if raw_first else "ServiceClient")
    company = ""
    role = ""
    resume_identifier = parts[-1] if len(parts) > 1 else stem
    candidate_name = "Candidate"
    status = "valid"
    error = None
    client_match = True

    # 1. Standard structured format without noise (e.g. Teksystems_Google_Data Analyst.pdf, Infosys_Amazon_QA.pdf)
    if len(parts) >= 2 and not has_noise:
        company = parts[1].upper() if len(parts[1]) <= 4 else parts[1].title()
        if len(parts) >= 3:
            role = format_role_title("_".join(parts[2:] if len(parts) == 3 else parts[2:-1]))
            candidate_name = _clean_candidate_name(parts[-1] if len(parts) >= 4 else parts[0])
        else:
            candidate_name = _clean_candidate_name(parts[0])

        if selected_client_name:
            if norm_first == norm_selected:
                service_client = selected_client_name
                status = "valid"
                client_match = True
                error = None
            else:
                # First segment is a distinct mismatching client name
                status = "needs_review"
                client_match = False
                error = "ServiceClient Mismatch"
        else:
            service_client = format_client_name(parts[0])
            status = "valid"
            client_match = True

    # 2. Natural / Candidate filenames (e.g. Suresh_resume (2).pdf, Suresh_resume.pdf, John_Doe.pdf)
    else:
        candidate_name = _clean_candidate_name(raw_first or stem)
        if selected_client_name:
            # Auto-assign selected ServiceClient
            service_client = selected_client_name
            status = "valid"
            client_match = True
            error = None
        else:
            service_client = "ServiceClient"
            status = "needs_review"
            client_match = False
            error = "Cannot detect ServiceClient from filename"

    return {
        "success": status == "valid",
        "service_client": service_client,
        "company": company or "General",
        "role": role or "General Role",
        "resume_identifier": resume_identifier or "RES01",
        "resume_id_tag": resume_identifier if (resume_identifier and bool(re.search(r'\d', resume_identifier))) else None,
        "candidate_name": candidate_name or "Candidate",
        "status": status,
        "client_match": client_match,
        "confidence": "high" if status == "valid" else "low",
        "error": error,
    }
