"""
Interview Intelligence Pipeline Orchestrator (v1.0 Production-Ready):
Coordinates the complete end-to-end ingestion flow:
1. Parse email (.eml, .pdf, or raw text)
2. Staging in Supabase Storage with atomic rollback
3. Sub-100ms Local Model classification with Calibrated Confidence
4. Groq AI Teacher Fallback on uncertainty (75-96% or <75%)
5. First-class conversation thread_id resolution / propagation
6. Active learning disagreement logging to teacher_disagreements
7. Application matching by company / role / domain with 3rd-party ATS filtering
8. Conversation threading & timeline event deduplication separating round from status
9. Database persistence and status updates
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview_intelligence.application_matcher import ApplicationMatcher
from app.modules.interview_intelligence.model import (
    ClassificationDecision,
    local_classifier,
)
from app.modules.interview_intelligence.models import EmailTrainingData
from app.modules.interview_intelligence.parser import EmailParser
from app.modules.interview_intelligence.schemas import (
    GroqTeacherResult,
    NormalizedEmail,
    ProcessEmailResponse,
)
from app.modules.interview_intelligence.storage import supabase_storage
from app.modules.interview_intelligence.teacher import groq_teacher
from app.modules.interview_intelligence.thread_matcher import ThreadMatcher

logger = logging.getLogger("interview_intelligence.orchestrator")


class InterviewPipelineOrchestrator:
    """Orchestrates end-to-end recruiter email intelligence ingestion."""

    @classmethod
    async def process_email(
        cls,
        session: AsyncSession,
        content: bytes | str,
        filename: str | None = None,
        mime_type: str | None = None,
        client_id: uuid.UUID | None = None,
        uploader_id: uuid.UUID | None = None,
    ) -> ProcessEmailResponse:
        """
        Executes complete unified pipeline for a single email file or text.
        """
        # Step 1: Parse Email
        parsed_email = EmailParser.parse_any(content, filename=filename, mime_type=mime_type)

        raw_bytes = content if isinstance(content, bytes) else content.encode("utf-8")
        file_ext = filename.split(".")[-1] if (filename and "." in filename) else "txt"

        # Step 2: Supabase Storage Staging with Retry-Safe Scope
        with supabase_storage.retry_safe_upload_scope() as staged_keys:
            raw_storage_key = supabase_storage.upload_raw_file(
                raw_bytes=raw_bytes,
                email_hash=parsed_email.email_hash,
                file_ext=file_ext,
                received_time=parsed_email.received_time,
            )
            staged_keys.append(raw_storage_key)
            parsed_email.raw_storage_key = raw_storage_key

            storage_key = supabase_storage.upload_normalized_json(
                email_data=parsed_email.to_storage_payload(),
                email_hash=parsed_email.email_hash,
                received_time=parsed_email.received_time,
            )
            staged_keys.append(storage_key)

            # Step 3: Resolve Conversation Thread ID
            thread_id = await ThreadMatcher.resolve_or_create_thread_id(session, parsed_email)

            # Step 4: Local Model Inference (< 15ms)
            local_pred = local_classifier.predict(parsed_email)
            decision = local_pred["decision"]
            confidence = local_pred["confidence"]

            company = None
            role = None
            round_name = None
            round_type = None
            status_value = None
            meeting_link = None
            deadline = None
            ai_reasoning = None
            source = "local"
            category = local_pred["category"]

            # Step 5: Decision Engine Routing
            if decision == ClassificationDecision.ACCEPT:
                # High-confidence local classification
                category = local_pred["category"]
                company = cls._heuristic_company_extract(parsed_email)
                meeting_link = cls._heuristic_meeting_link(parsed_email)
                round_name = ThreadMatcher._default_round_name(category)
                round_type = ThreadMatcher._infer_round_type(category, round_name)
                status_value = ThreadMatcher._default_status(category)
                ai_reasoning = f"Directly accepted by local calibrated model ({confidence}% confidence)."
            else:
                # Escalate to Groq Teacher (75-96% or <75%)
                teacher_res: GroqTeacherResult = await groq_teacher.classify_with_teacher(
                    email_data=parsed_email,
                    local_prediction=local_pred,
                )
                category = teacher_res.category
                company = teacher_res.company or cls._heuristic_company_extract(parsed_email)
                role = teacher_res.role
                round_name = teacher_res.round_name or teacher_res.round
                round_type = teacher_res.round_type
                status_value = teacher_res.status
                meeting_link = teacher_res.meeting_link or cls._heuristic_meeting_link(parsed_email)
                deadline = teacher_res.deadline
                confidence = teacher_res.confidence
                source = "groq"
                ai_reasoning = teacher_res.reason

            # Step 6: Create Database Training Record with thread_id
            email_record = EmailTrainingData(
                id=uuid.uuid4(),
                version=1,
                thread_id=thread_id,
                message_id=parsed_email.message_id,
                in_reply_to=parsed_email.in_reply_to,
                email_hash=parsed_email.email_hash,
                subject=parsed_email.subject,
                sender_email=parsed_email.sender_email,
                sender_domain=parsed_email.sender_domain,
                sender_name=parsed_email.sender_name,
                body_preview=parsed_email.body_preview,
                storage_key=storage_key,
                raw_storage_key=raw_storage_key,
                body_sha256=parsed_email.body_sha256,
                attachment_metadata=parsed_email.attachment_metadata,
                company=company,
                role=role,
                category=category,
                confidence=confidence,
                source=source,
                classification_source_version=f"{source}_v1.0",
                pipeline_version="interview_pipeline_v2.0",
                needs_retraining=False,
                ai_reasoning=ai_reasoning,
                processing_status="classified",
            )
            session.add(email_record)

            # Step 7: Log Disagreement for Active Learning (if Local != Groq)
            if source == "groq":
                await groq_teacher.log_disagreement_if_any(
                    session=session,
                    email_record=email_record,
                    local_prediction=local_pred,
                    teacher_result=teacher_res,
                )

            # Step 8: Application Matching with 3rd-party ATS precedence
            matched_app = await ApplicationMatcher.match_application(
                session=session,
                company=company,
                role=role,
                sender_domain=parsed_email.sender_domain,
                subject=parsed_email.subject,
                body_text=parsed_email.body,
                client_id=client_id,
            )
            app_id = matched_app.id if matched_app else None
            if matched_app and not company:
                company = matched_app.company

            # Step 9: Thread & Event Timeline Deduplication
            action, event_record = await ThreadMatcher.match_and_deduplicate_event(
                session=session,
                email_record=email_record,
                email_data=parsed_email,
                category=category,
                company=company,
                role=role,
                round_name=round_name,
                round_type=round_type,
                status_value=status_value,
                meeting_link=meeting_link,
                deadline=deadline,
                thread_id=thread_id,
                application_id=app_id,
            )

            # Step 10: Sync Matched Application Status
            if matched_app:
                await ApplicationMatcher.sync_application_status(
                    session=session,
                    application=matched_app,
                    category=category,
                    round_name=round_name,
                    meeting_link=meeting_link,
                    email_preview=parsed_email.body_preview,
                )

            await session.commit()

            return ProcessEmailResponse(
                status="success",
                action=action,
                email_id=email_record.id,
                email_hash=email_record.email_hash,
                thread_id=thread_id,
                category=category,
                confidence=confidence,
                decision=decision,
                source=source,
                company=company,
                role=role,
                round_name=event_record.round_name if event_record else round_name,
                round_type=event_record.round_type if event_record else round_type,
                round=event_record.round_name if event_record else (round_name or None),
                event_sequence=event_record.event_sequence if event_record else None,
                event_id=event_record.id if event_record else None,
                application_id=app_id,
                meeting_link=meeting_link,
                deadline=deadline,
                ai_reasoning=ai_reasoning,
                needs_retraining=email_record.needs_retraining,
                pipeline_version="interview_pipeline_v2.0",
            )

    @staticmethod
    def _heuristic_company_extract(email: NormalizedEmail) -> str | None:
        """Extracts plausible company name from subject or sender domain (excluding ATS platforms)."""
        ignored = {
            "greenhouse", "lever", "workday", "ashby", "ashbyhq", "smartrecruiters", "gmail",
            "outlook", "yahoo", "hackerrank", "codesignal", "codility", "coderpad",
            "calendly", "zoom", "google", "microsoft", "testgorilla", "hirevue"
        }
        if email.sender_domain and "." in email.sender_domain:
            root = email.sender_domain.split(".")[0].strip().lower()
            if root not in ignored and len(root) >= 3:
                return root.capitalize()

        if email.subject:
            # Common formats: "Stripe Online Technical Assessment", "Amazon Interview"
            words = [w.strip() for w in email.subject.split() if len(w.strip()) >= 3]
            skip_words = {"interview", "technical", "screening", "assessment", "invitation", "application", "details", "update", "round", "online", "take-home", "with", "from", "your", "for"}
            for w in words:
                if w.lower() not in skip_words and w.lower() not in ignored:
                    return w.capitalize()

        return None

    @staticmethod
    def _heuristic_meeting_link(email: NormalizedEmail) -> str | None:
        """Extracts meeting link from links list."""
        for link in email.links:
            if any(p in link.lower() for p in ["zoom.us", "meet.google.com", "teams.microsoft.com", "calendly.com"]):
                return link
        return None


# Global singleton instance
pipeline_orchestrator = InterviewPipelineOrchestrator()
