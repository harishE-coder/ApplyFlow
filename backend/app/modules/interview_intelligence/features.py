"""
Feature extraction engine for recruiter email classification.
Builds enriched multi-signal feature representations combining:
- Subject headers
- Sender domain and email
- Link domains (Zoom, HackerRank, CodeSignal, Calendly, Google Meet)
- Attachment types (.ics calendar invites, .pdf take-home instructions)
- Binary tokens: HAS_ICS=1, HAS_MEETING_LINK=1, HAS_DEADLINE=1
- Cleaned body content
"""

import re
from typing import Any
from urllib.parse import urlparse

from app.modules.interview_intelligence.schemas import NormalizedEmail

# High-signal platform domains
INTERVIEW_PLATFORMS = {
    "zoom.us", "meet.google.com", "teams.microsoft.com", "webex.com",
    "chime.aws", "bluejeans.com", "whereby.com"
}
ASSESSMENT_PLATFORMS = {
    "hackerrank.com", "codesignal.com", "codility.com", "coderpad.io",
    "leetcode.com", "karat.com", "hirevue.com", "testgorilla.com",
    "glider.ai", "qualified.io", "codewars.com"
}
SCHEDULING_PLATFORMS = {
    "calendly.com", "calendar.google.com", "outlook.office365.com",
    "goodtime.io", "chilipiper.com", "cron.com", "savvycal.com"
}
ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "workday.com", "ashbyhq.com",
    "smartrecruiters.com", "jobvite.com", "icims.com", "myworkdayjobs.com",
    "recruitee.com", "breezy.hr", "workable.com"
}

DEADLINE_PATTERN = re.compile(
    r"\b(?:within\s+\d+\s+(?:hours?|days?)|expires?\s+in|complete\s+(?:by|within)|due\s+(?:date|by|on)|by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|deadline\s+is|submit\s+by)\b",
    re.IGNORECASE,
)


def extract_domain_from_url(url: str) -> str:
    """Extracts lowercase domain/host from a URL string."""
    if not url:
        return ""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        host = (parsed.netloc or parsed.path.split("/")[0]).lower().strip()
        host = host.split(":")[0]
        host = host.removeprefix("www.")
        return host
    except Exception:
        return ""


def extract_link_domains(links: list[str]) -> list[str]:
    """Extracts unique sorted link domains from list of URLs."""
    domains = set()
    for link in links or []:
        dom = extract_domain_from_url(link)
        if dom and "." in dom:
            domains.add(dom)
    return sorted(list(domains))


def extract_attachment_signals(attachment_names: list[str]) -> list[str]:
    """Extracts normalized attachment names and file extensions."""
    signals = set()
    for name in attachment_names or []:
        clean_name = str(name).strip().lower()
        if not clean_name:
            continue
        signals.add(clean_name)
        if "." in clean_name:
            ext = "." + clean_name.split(".")[-1]
            signals.add(ext)
    return sorted(list(signals))


def extract_domain_signals(links: list[str]) -> dict[str, bool]:
    """Extracts boolean flags for presence of critical domain classes (supporting subdomains)."""
    domains = set(extract_link_domains(links))

    def _matches_any(target_set: set[str]) -> bool:
        for d in domains:
            for target in target_set:
                if d == target or d.endswith("." + target):
                    return True
        return False

    return {
        "has_interview_platform": _matches_any(INTERVIEW_PLATFORMS),
        "has_assessment_platform": _matches_any(ASSESSMENT_PLATFORMS),
        "has_scheduling_platform": _matches_any(SCHEDULING_PLATFORMS),
        "has_ats_domain": _matches_any(ATS_DOMAINS),
    }


def build_feature_text(email_input: NormalizedEmail | dict[str, Any]) -> str:
    """
    Constructs a rich, canonical feature text combining all signals:
    SUBJECT: ...
    SENDER_DOMAIN: ...
    SENDER_EMAIL: ...
    LINK_DOMAINS: ...
    ATTACHMENTS: ...
    BINARY_SIGNALS: HAS_ICS=1 HAS_MEETING_LINK=1 HAS_DEADLINE=1
    BODY: ...
    """
    if isinstance(email_input, NormalizedEmail):
        subject = email_input.subject or ""
        sender_domain = email_input.sender_domain or ""
        sender_email = email_input.sender_email or ""
        links = email_input.links or []
        attachments = email_input.attachment_names or []
        body = email_input.body or ""
    elif isinstance(email_input, dict):
        subject = str(email_input.get("subject") or "")
        sender_domain = str(email_input.get("sender_domain") or "")
        sender_email = str(email_input.get("sender_email") or "")
        links = email_input.get("links") or []
        attachments = email_input.get("attachment_names") or []
        body = str(email_input.get("body") or "")
    else:
        return ""

    link_domains = extract_link_domains(links)
    attachment_signals = extract_attachment_signals(attachments)
    domain_sigs = extract_domain_signals(links)

    has_ics = 1 if any(".ics" in s or "invite.ics" in s for s in attachment_signals) else 0
    has_meeting_link = 1 if domain_sigs["has_interview_platform"] or domain_sigs["has_scheduling_platform"] else 0
    has_deadline = 1 if DEADLINE_PATTERN.search(body) or DEADLINE_PATTERN.search(subject) else 0

    parts = [
        f"SUBJECT: {subject.strip()}",
        f"SENDER_DOMAIN: {sender_domain.strip().lower()}",
        f"SENDER_EMAIL: {sender_email.strip().lower()}",
        f"LINK_DOMAINS: {' '.join(link_domains)}",
        f"ATTACHMENTS: {' '.join(attachment_signals)}",
        f"SIGNALS: HAS_ICS={has_ics} HAS_MEETING_LINK={has_meeting_link} HAS_DEADLINE={has_deadline}",
        f"BODY: {body.strip()}",
    ]
    return "\n".join(parts)
