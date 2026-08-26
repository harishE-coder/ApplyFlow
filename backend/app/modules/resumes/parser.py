"""
ApplyFlow Official Resume Filename Standard & Parser
Locked Format:
ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf

Examples:
- ABCStaffing_TCS_JavaDeveloper_RES101.pdf
- TalentHub_Amazon_SDEII_RES205.pdf
- NextHire_Infosys_INF-PY-02_RahulKumar.pdf
"""

import re
from pathlib import Path


def _normalize_client_name(name: str | None) -> str:
    """Normalize client name for case-insensitive and whitespace-insensitive comparison."""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()


def format_role_title(role_raw: str) -> str:
    """Format role names and preserve role codes."""
    if not role_raw:
        return "General Role"

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


def format_client_name(client_raw: str) -> str:
    """Format client names nicely from filename segment."""
    if not client_raw:
        return "General Client"
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', client_raw)
    spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)
    return spaced.strip()


def parse_resume_filename(filename: str, selected_client_name: str | None = None) -> dict:
    """
    Parse ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf.

    Expected 4 segments:
    - PART 1 = Service Client (e.g. ABCStaffing, TalentHub, NextHire)
    - PART 2 = Company (e.g. TCS, Amazon, Infosys)
    - PART 3 = Role or Role ID (e.g. JavaDeveloper, SDEII, INF-PY-02, TCS-JAVA-01)
    - PART 4 = Resume Identifier (e.g. RES101, RES205, RahulKumar)
    """
    stem = Path(filename).stem.strip()
    # Split by underscore
    parts = [p.strip() for p in stem.split('_') if p.strip()]

    # Segment count rule (Rule 2: Require at least 4 segments)
    if len(parts) < 4:
        comp = parts[0].upper() if len(parts) >= 1 and len(parts[0]) <= 4 else (parts[0].title() if len(parts) >= 1 else "General")
        r_title = parts[1] if len(parts) >= 2 else ""
        return {
            "success": False,
            "service_client": format_client_name(parts[0]) if len(parts) >= 1 else "Unknown Client",
            "company": comp,
            "role": format_role_title(r_title),
            "resume_identifier": parts[-1] if len(parts) >= 1 else "",
            "resume_id_tag": parts[-1] if len(parts) >= 1 else None,
            "candidate_name": stem.replace("_", " ").title(),
            "client_match": False,
            "confidence": "low",
            "error": "Invalid filename format. Expected: ServiceClient_Company_RoleOrRoleID_ResumeIdentifier.pdf",
        }

    # Exactly 4 or more segments
    raw_client = parts[0]
    raw_company = parts[1]
    raw_role_parts = parts[2:-1]
    raw_identifier = parts[-1]

    service_client = format_client_name(raw_client)
    company = raw_company.upper() if len(raw_company) <= 4 else raw_company.title()
    role = format_role_title("_".join(raw_role_parts))
    resume_identifier = raw_identifier

    # Candidate Name & Resume ID Tag
    resume_id_tag = resume_identifier
    id_match = re.search(r'^(RES\d+|Resume\d+|\d+)$', resume_identifier, re.IGNORECASE)
    if id_match:
        resume_id_tag = id_match.group(0).upper()
        candidate_name = f"Candidate {resume_id_tag}"
    else:
        name_spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', resume_identifier)
        candidate_name = name_spaced.replace("_", " ").title()

    # Rule 1: Service Client match check
    client_match = True
    error_msg = None
    if selected_client_name:
        norm_parsed = _normalize_client_name(raw_client)
        norm_selected = _normalize_client_name(selected_client_name)
        if norm_parsed != norm_selected:
            client_match = False
            error_msg = f"Filename client '{raw_client}' does not match selected Service Client '{selected_client_name}'."
        else:
            service_client = selected_client_name

    return {
        "success": client_match,
        "service_client": service_client,
        "company": company,
        "role": role,
        "resume_identifier": resume_identifier,
        "resume_id_tag": resume_id_tag,
        "candidate_name": candidate_name,
        "client_match": client_match,
        "confidence": "high" if client_match else "low",
        "error": error_msg,
    }
