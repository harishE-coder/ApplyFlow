"""
Groq AI Teacher Engine (Stage 3):
- Uses Groq Llama 3.3 70B (llama-3.3-70b-versatile) with temperature=0.1
- Enforces strict deterministic JSON extraction
- Separates dynamic round_name from event status and normalized round_type (Enum)
- Employs third-party ATS domain filtering for clean company extraction
- Compares Local Classifier predictions with AI Teacher classifications
- Automatically logs disagreements to teacher_disagreements for active learning
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import chat_completion
from app.modules.interview_intelligence.models import (
    EmailTrainingData,
    TeacherDisagreement,
)
from app.modules.interview_intelligence.schemas import (
    EmailCategory,
    EventStatus,
    GroqTeacherResult,
    NormalizedEmail,
    RoundType,
)

logger = logging.getLogger("interview_intelligence.teacher")

IGNORED_ATS_DOMAINS = {
    "greenhouse.io", "lever.co", "ashbyhq.com", "myworkday.com", "workday.com",
    "smartrecruiters.com", "workablemail.com", "bamboohr.com", "jobvite.com",
    "taleo.net", "icims.com", "hirevue.com", "testgorilla.com", "hackerrank.com",
    "codesignal.com", "codility.com", "coderpad.io", "gmail.com", "outlook.com", "yahoo.com"
}


class GroqTeacherService:
    """Service to invoke Groq API for deterministic structured recruiting intelligence extraction."""

    def __init__(self, prompt_version: str = "teacher_v1"):
        self.prompt_version = prompt_version
        self._prompt_template: str | None = None

    def _get_prompt_template(self) -> str:
        """Loads versioned system prompt markdown template from prompts directory."""
        if self._prompt_template is None:
            prompt_path = Path(__file__).parent / "prompts" / f"interview_{self.prompt_version}.md"
            if prompt_path.exists():
                self._prompt_template = prompt_path.read_text(encoding="utf-8")
            else:
                self._prompt_template = (
                    "You are a Senior Recruiter AI Teacher. Extract JSON with keys: "
                    "it_related (bool), category (string), company (string), role (string), "
                    "round_name (string), round_type (string), status (string), confidence (int), "
                    "meeting_link (string), deadline (string), reason (string)."
                )
        return self._prompt_template

    def build_user_payload(
        self,
        email_data: NormalizedEmail | dict[str, Any],
        local_prediction: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Constructs sanitized payload for Groq prompt input."""
        if isinstance(email_data, NormalizedEmail):
            payload = {
                "subject": email_data.subject,
                "sender_email": email_data.sender_email,
                "sender_domain": email_data.sender_domain,
                "body": email_data.body,
                "links": email_data.links,
                "attachments": email_data.attachment_names,
            }
        else:
            payload = {
                "subject": email_data.get("subject", ""),
                "sender_email": email_data.get("sender_email", ""),
                "sender_domain": email_data.get("sender_domain", ""),
                "body": email_data.get("body", ""),
                "links": email_data.get("links", []),
                "attachments": email_data.get("attachment_names", []),
            }

        if local_prediction:
            payload["local_model_prediction"] = {
                "category": local_prediction.get("category"),
                "confidence": local_prediction.get("confidence"),
                "decision": local_prediction.get("decision"),
            }

        return payload

    async def classify_with_teacher(
        self,
        email_data: NormalizedEmail | dict[str, Any],
        local_prediction: dict[str, Any] | None = None,
    ) -> GroqTeacherResult:
        """
        Invokes AI Gateway to extract structured JSON with multi-key failover.
        Falls back gracefully if AI API keys are not configured or in offline mode.
        """
        system_prompt = self._get_prompt_template()
        user_content = json.dumps(self.build_user_payload(email_data, local_prediction), ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            data = await chat_completion(
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=20.0,
            )
            raw_json_str = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_json_str)

            if "error" in parsed or data.get("model") == "offline-fallback" or not parsed.get("category"):
                raise ValueError("AI Gateway offline fallback returned")

            # Validate and normalize category, round_type, and status
            category = self._normalize_category(parsed.get("category"))
            round_type = self._normalize_round_type(parsed.get("round_type"), category)
            event_status = self._normalize_status(parsed.get("status"), category)
            round_name = parsed.get("round_name") or parsed.get("round")
            company = self._clean_company(parsed.get("company"), email_data)

            return GroqTeacherResult(
                it_related=bool(parsed.get("it_related", True)),
                category=category,
                company=company,
                role=parsed.get("role"),
                round_name=round_name,
                round_type=round_type,
                status=event_status,
                round=round_name,
                confidence=int(parsed.get("confidence", 95)),
                meeting_link=parsed.get("meeting_link"),
                deadline=parsed.get("deadline"),
                reason=str(parsed.get("reason", "AI Gateway structured extraction.")),
                prompt_version=self.prompt_version,
            )
        except Exception as e:
            logger.warning(f"AI Gateway Teacher call error ({e}). Using deterministic heuristic fallback.")
            return self._heuristic_offline_teacher(email_data, local_prediction)

    def _clean_company(self, extracted_company: str | None, email_data: Any) -> str | None:
        """Filters out third-party ATS platforms (greenhouse, lever, ashby) from company name."""
        if extracted_company:
            clean = extracted_company.strip()
            if clean.lower() not in {"greenhouse", "lever", "ashby", "workday", "smartrecruiters", "jobvite"}:
                return clean

        # Heuristic fallback: check subject line
        subject = email_data.subject if isinstance(email_data, NormalizedEmail) else email_data.get("subject", "")
        if subject:
            words = [w.strip() for w in subject.split() if len(w.strip()) >= 3]
            skip_words = {"interview", "technical", "screening", "assessment", "invitation", "application", "details", "update", "round", "online", "take-home", "with", "from", "your", "for"}
            for w in words:
                if w.lower() not in skip_words and w.lower() not in {"greenhouse", "lever", "ashby", "workday"}:
                    return w.capitalize()

        return None

    def _normalize_category(self, raw_category: str | None) -> str:
        """Ensures category matches one of 13 canonical label taxonomy values."""
        if not raw_category:
            return EmailCategory.OTHER.value
        clean = raw_category.strip().lower().replace(" ", "_").replace("-", "_")
        valid_cats = {c.value for c in EmailCategory}
        if clean in valid_cats:
            return clean

        # Taxonomy fallback mapping
        mapping = {
            "interview_invitation": EmailCategory.INTERVIEW.value,
            "screening": EmailCategory.HR_SCREENING.value,
            "online_assessment": EmailCategory.TECHNICAL_ASSESSMENT.value,
            "assessment": EmailCategory.TECHNICAL_ASSESSMENT.value,
            "coding_challenge": EmailCategory.TECHNICAL_ASSESSMENT.value,
            "takehome": EmailCategory.TAKE_HOME.value,
            "assignment": EmailCategory.TAKE_HOME.value,
            "confirmed": EmailCategory.INTERVIEW_CONFIRMATION.value,
            "reschedule": EmailCategory.INTERVIEW_RESCHEDULE.value,
            "cancelled": EmailCategory.INTERVIEW_CANCELLED.value,
            "canceled": EmailCategory.INTERVIEW_CANCELLED.value,
            "followup": EmailCategory.RECRUITER_FOLLOWUP.value,
            "offer_letter": EmailCategory.APPLICATION_UPDATE.value,
        }
        return mapping.get(clean, EmailCategory.OTHER.value)

    def _normalize_round_type(self, raw_type: str | None, category: str) -> str:
        """Normalizes round_type to strict RoundType Enum."""
        if raw_type:
            clean = raw_type.strip().lower().replace(" ", "_").replace("-", "_")
            valid_types = {r.value for r in RoundType}
            if clean in valid_types:
                return clean

        mapping = {
            EmailCategory.HR_SCREENING.value: RoundType.HR_SCREENING.value,
            EmailCategory.TECHNICAL_ASSESSMENT.value: RoundType.TECHNICAL_ASSESSMENT.value,
            EmailCategory.TAKE_HOME.value: RoundType.TECHNICAL_ASSESSMENT.value,
            EmailCategory.INTERVIEW.value: RoundType.INTERVIEW.value,
            EmailCategory.INTERVIEW_CONFIRMATION.value: RoundType.INTERVIEW.value,
            EmailCategory.INTERVIEW_RESCHEDULE.value: RoundType.INTERVIEW.value,
            EmailCategory.REJECTION.value: RoundType.REJECTION.value,
        }
        return mapping.get(category, RoundType.OTHER.value)

    def _normalize_status(self, raw_status: str | None, category: str) -> str:
        """Normalizes status to strict EventStatus Enum."""
        if raw_status:
            clean = raw_status.strip().capitalize()
            valid_statuses = {s.value for s in EventStatus}
            if clean in valid_statuses:
                return clean

        mapping = {
            EmailCategory.INTERVIEW_CONFIRMATION.value: EventStatus.CONFIRMED.value,
            EmailCategory.INTERVIEW_RESCHEDULE.value: EventStatus.RESCHEDULED.value,
            EmailCategory.INTERVIEW_CANCELLED.value: EventStatus.CANCELLED.value,
            EmailCategory.REJECTION.value: EventStatus.REJECTED.value,
        }
        return mapping.get(category, EventStatus.SCHEDULED.value)

    def _heuristic_offline_teacher(
        self,
        email_data: NormalizedEmail | dict[str, Any],
        local_prediction: dict[str, Any] | None = None,
    ) -> GroqTeacherResult:
        """Deterministic rule-based extractor used in offline / test environments."""
        body = email_data.body.lower() if isinstance(email_data, NormalizedEmail) else email_data.get("body", "").lower()
        subj = email_data.subject.lower() if isinstance(email_data, NormalizedEmail) else email_data.get("subject", "").lower()
        links = email_data.links if isinstance(email_data, NormalizedEmail) else email_data.get("links", [])
        attachments = email_data.attachment_names if isinstance(email_data, NormalizedEmail) else email_data.get("attachment_names", [])
        sender_domain = email_data.sender_domain if isinstance(email_data, NormalizedEmail) else email_data.get("sender_domain", "")

        # Extract meeting link
        meeting_link = next(
            (link for link in links if any(p in link.lower() for p in ["zoom.us", "meet.google.com", "teams.microsoft.com", "calendly.com"])),
            None,
        )

        # Extract deadline
        deadline_match = re.search(r"(?:within\s+\d+\s+(?:hours|days)|by\s+[a-zA-Z]+|expires\s+in\s+\d+\s+days)", body)
        deadline = deadline_match.group(0) if deadline_match else None

        # Clean Company extraction
        company = self._clean_company(None, email_data)
        if not company and sender_domain and "." in sender_domain:
            domain_root = sender_domain.split(".")[0].strip().lower()
            if domain_root not in {"greenhouse", "lever", "ashby", "workday", "smartrecruiters", "gmail", "outlook", "yahoo"}:
                company = domain_root.capitalize()

        # Classification logic
        if any(w in body or w in subj for w in ["hackerrank", "codesignal", "codility", "online assessment"]):
            cat = EmailCategory.TECHNICAL_ASSESSMENT.value
            round_name = "Online Assessment"
            round_type = RoundType.TECHNICAL_ASSESSMENT.value
            status = EventStatus.SCHEDULED.value
            reason = "Detected coding assessment platform and test instructions."
        elif any(w in body or w in subj for w in ["take-home", "take home", "project assignment", "github.com/"]):
            cat = EmailCategory.TAKE_HOME.value
            round_name = "Take-Home Assignment"
            round_type = RoundType.TECHNICAL_ASSESSMENT.value
            status = EventStatus.SCHEDULED.value
            reason = "Detected take-home engineering assignment."
        elif any(w in body or w in subj for w in ["reschedule", "conflict", "new time slot"]):
            cat = EmailCategory.INTERVIEW_RESCHEDULE.value
            round_name = "Interview Reschedule"
            round_type = RoundType.INTERVIEW.value
            status = EventStatus.RESCHEDULED.value
            reason = "Detected interview rescheduling request."
        elif any(w in body or w in subj for w in ["confirmed", "calendar invite", "scheduled for"]) or any(".ics" in a for a in attachments):
            cat = EmailCategory.INTERVIEW_CONFIRMATION.value
            round_name = "Interview Confirmed"
            round_type = RoundType.INTERVIEW.value
            status = EventStatus.CONFIRMED.value
            reason = "Detected calendar confirmation."
        elif any(w in body or w in subj for w in ["unfortunately", "pursue other candidates", "not moving forward"]):
            cat = EmailCategory.REJECTION.value
            round_name = "Application Closed"
            round_type = RoundType.REJECTION.value
            status = EventStatus.REJECTED.value
            reason = "Detected candidate rejection notice."
        elif any(w in body or w in subj for w in ["screening", "recruiter chat", "introductory call"]):
            cat = EmailCategory.HR_SCREENING.value
            round_name = "Recruiter Screen"
            round_type = RoundType.HR_SCREENING.value
            status = EventStatus.SCHEDULED.value
            reason = "Detected introductory recruiter screening."
        elif any(w in body or w in subj for w in ["interview", "technical round", "system design", "bar raiser"]):
            cat = EmailCategory.INTERVIEW.value
            round_name = "Bar Raiser" if "bar raiser" in body or "bar raiser" in subj else "Technical Interview"
            round_type = RoundType.INTERVIEW.value
            status = EventStatus.SCHEDULED.value
            reason = "Detected technical interview round invitation."
        elif local_prediction and local_prediction.get("category"):
            cat = local_prediction["category"]
            round_name = "Interview Round"
            round_type = RoundType.INTERVIEW.value
            status = EventStatus.SCHEDULED.value
            reason = "Teacher concurred with local model confidence."
        else:
            cat = EmailCategory.OTHER.value
            round_name = "Communication"
            round_type = RoundType.OTHER.value
            status = EventStatus.PENDING.value
            reason = "General recruiting notification."

        return GroqTeacherResult(
            it_related=True,
            category=cat,
            company=company,
            role="Software Engineer",
            round_name=round_name,
            round_type=round_type,
            status=status,
            round=round_name,
            confidence=98,
            meeting_link=meeting_link,
            deadline=deadline,
            reason=reason,
            prompt_version=self.prompt_version,
        )

    async def log_disagreement_if_any(
        self,
        session: AsyncSession,
        email_record: EmailTrainingData,
        local_prediction: dict[str, Any],
        teacher_result: GroqTeacherResult,
    ) -> TeacherDisagreement | None:
        """
        Compares Local Model prediction vs Groq Teacher result.
        If they disagree, logs to teacher_disagreements table and flags needs_retraining=True.
        """
        local_cat = local_prediction.get("category")
        ai_cat = teacher_result.category

        if local_cat and ai_cat and local_cat != ai_cat:
            disagreement = TeacherDisagreement(
                email_id=email_record.id,
                local_label=local_cat,
                local_confidence=local_prediction.get("confidence"),
                ai_label=ai_cat,
                ai_confidence=teacher_result.confidence,
                human_label=None,
                resolved=False,
                notes=f"Local: {local_cat} vs AI: {ai_cat}. Reason: {teacher_result.reason}",
            )
            session.add(disagreement)
            email_record.needs_retraining = True
            logger.info(f"Disagreement logged for email {email_record.id}: Local={local_cat} vs AI={ai_cat}")
            return disagreement

        return None


# Global singleton instance
groq_teacher = GroqTeacherService(prompt_version="teacher_v1")
