"""
Resume filename parser for Apply Flow Careers.
Parses patterns like:
- TCS_JavaDeveloper_Harish.pdf
- TCS_JavaDeveloper_RES1023.pdf
- Amazon_Frontend_Resume145.pdf
- Infosys_PythonDeveloper_RahulSharma.pdf
"""

import re
from pathlib import Path


def parse_resume_filename(filename: str) -> dict:
    """
    Parse company, role, and candidate name / resume ID from filename.
    Returns:
        {
            "success": bool,
            "company": str,
            "role": str,
            "candidate_name": str,
            "resume_id_tag": str | None,
            "confidence": "high" | "low",
            "error": str | None
        }
    """
    stem = Path(filename).stem.strip()

    cleaned = re.sub(r'[\s\-]+', '_', stem)
    parts = [p.strip() for p in cleaned.split('_') if p.strip()]

    if len(parts) >= 3:
        company = parts[0]
        role_parts = parts[1:-1]
        role = " ".join(re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', "".join(role_parts))) or "_".join(role_parts)
        if not role or len(role) < 2:
            role = " ".join(role_parts)

        last_part = parts[-1]
        resume_id_tag = None
        candidate_name = last_part

        id_match = re.search(r'(RES\d+|Resume\d+|\d+)', last_part, re.IGNORECASE)
        if id_match and len(id_match.group(0)) >= 3:
            resume_id_tag = id_match.group(0).upper()
            candidate_name = f"Candidate {resume_id_tag}"
        else:
            candidate_words = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z]|$)|[a-z]+', last_part)
            if candidate_words:
                candidate_name = " ".join(candidate_words)

        return {
            "success": True,
            "company": company.upper() if len(company) <= 4 else company.title(),
            "role": role.title(),
            "candidate_name": candidate_name.title(),
            "resume_id_tag": resume_id_tag,
            "confidence": "high",
            "error": None,
        }

    elif len(parts) == 2:
        return {
            "success": False,
            "company": parts[0].title(),
            "role": parts[1].replace("_", " ").title(),
            "candidate_name": "Unspecified Candidate",
            "resume_id_tag": None,
            "confidence": "low",
            "error": "Missing candidate name or role in filename",
        }

    return {
        "success": False,
        "company": "General",
        "role": "",
        "candidate_name": stem.replace("_", " ").title(),
        "resume_id_tag": None,
        "confidence": "low",
        "error": "Filename format should be Company_Role_Candidate.pdf",
    }
