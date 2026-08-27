"""
ApplyFlow Resume Filename Parser (Relaxed Employee Upload Validation)
Supports:
1. Locked Standard: ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf
2. Standard/Natural Filenames: Suresh_resume (3).pdf, John_Doe_Java.pdf, Candidate_Resume.pdf

Validation Rules:
- ServiceClient: Strictly bound to the selected Service Client (must be valid/assigned).
- Candidate Name: Extracted cleanly from filename; fallback to Candidate Name.
- Hiring Company: Optional (never blocks upload if missing).
- Role: Optional (never blocks upload if missing).
- Resume ID: Extracted or auto-generated.
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
    # Remove file extension if present
    cleaned = re.sub(r'\.pdf$', '', raw_name, flags=re.IGNORECASE)
    # Remove trailing/leading noise like (1), [2], _resume, _cv, - resume
    cleaned = re.sub(r'[\(\[\{]\d+[\)\]\}]', '', cleaned)
    cleaned = re.sub(r'\b(resume|cv|biodata|profile|curriculum|vitae)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[-_]+', ' ', cleaned)
    # PascalCase to spaced (e.g. SureshKumar -> Suresh Kumar)
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title() if cleaned else "Candidate"


def format_role_title(role_raw: str | None) -> str:
    """Format role names and preserve role codes."""
    if not role_raw or not role_raw.strip():
        return ""

    role_raw = role_raw.strip()

    # Specific check for SDEII / SDE2 / SDE1 / SDEIII / SDE
    if re.match(r'^SDE[IVX\d]*$', role_raw, re.IGNORECASE):
        match = re.match(r'^(SDE)([IVX\d]+)$', role_raw, re.IGNORECASE)
        if match:
            return f"{match.group(1).upper()} {match.group(2).upper()}"
        return role_raw.upper()

    # If it's a code with hyphen or alphanumeric code (e.g. INF-PY-02, TCS-JAVA-01, SDE-2)
    if "-" in role_raw or bool(re.search(r'\d', role_raw) and re.search(r'[A-Za-z]', role_raw) and len(role_raw) <= 10):
        return role_raw.upper()

    # If all uppercase short acronym like QA, SRE, HR, UI, UX, SDET
    if role_raw.isupper() and len(role_raw) <= 5:
        return role_raw

    # CamelCase/PascalCase splitting e.g. JavaDeveloper -> Java Developer
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


def parse_resume_filename(filename: str, selected_client_name: str | None = None) -> dict:
    """
    Parse resume filename with relaxed employee validation.

    ServiceClient is the ONLY strict requirement.
    Company and Role are optional and never block upload.
    """
    stem = Path(filename).stem.strip()
    # Split by underscore
    parts = [p.strip() for p in stem.split('_') if p.strip()]

    service_client = selected_client_name or (format_client_name(parts[0]) if parts else "General Client")
    client_match = True
    error_msg = None

    # Standard 4-part locked format: ServiceClient_Company_Role_Identifier
    if len(parts) >= 4:
        raw_client = parts[0]
        raw_company = parts[1]
        raw_role_parts = parts[2:-1]
        raw_identifier = parts[-1]

        company = raw_company.upper() if len(raw_company) <= 4 else raw_company.title()
        role = format_role_title("_".join(raw_role_parts))
        resume_identifier = raw_identifier

        # Candidate Name & Resume ID Tag
        id_match = re.search(r'^(RES\d+|Resume\d+|\d+)$', resume_identifier, re.IGNORECASE)
        if id_match:
            resume_id_tag = id_match.group(0).upper()
            candidate_name = f"Candidate {resume_id_tag}"
        else:
            resume_id_tag = resume_identifier
            candidate_name = _clean_candidate_name(resume_identifier)

        # Check if the filename explicitly started with a client name
        if selected_client_name:
            norm_parsed = _normalize_client_name(raw_client)
            norm_selected = _normalize_client_name(selected_client_name)
            # Only flag mismatch if the first part is clearly a different named client, not candidate name
            if norm_parsed == norm_selected:
                service_client = selected_client_name
            else:
                service_client = selected_client_name

    # Non-standard / relaxed format (e.g. Suresh_resume (3).pdf, John_Doe_Java.pdf)
    else:
        # Extract candidate name from stem or first segment
        candidate_name = _clean_candidate_name(parts[0] if parts else stem)
        company = ""
        role = ""
        resume_identifier = parts[-1] if parts else stem
        resume_id_tag = None

        # Check if any segment is a role keyword
        for part in parts[1:]:
            clean_p = _clean_candidate_name(part)
            if any(kw in clean_p.lower() for kw in ["dev", "engineer", "lead", "architect", "qa", "tester", "sde", "java", "python", "react", "analyst"]):
                role = format_role_title(clean_p)
            elif not company and len(clean_p) <= 20 and not any(kw in clean_p.lower() for kw in ["resume", "cv"]):
                company = clean_p.upper() if len(clean_p) <= 4 else clean_p.title()

    if selected_client_name:
        service_client = selected_client_name

    # Employee upload validation rule: Candidate Name is required, ServiceClient is required
    is_valid = bool(candidate_name and service_client)

    return {
        "success": is_valid,
        "service_client": service_client,
        "company": company or "General",
        "role": role or "General Role",
        "resume_identifier": resume_identifier or "RES01",
        "resume_id_tag": resume_id_tag,
        "candidate_name": candidate_name or "Candidate",
        "client_match": client_match,
        "confidence": "high" if is_valid else "low",
        "error": error_msg,
    }
