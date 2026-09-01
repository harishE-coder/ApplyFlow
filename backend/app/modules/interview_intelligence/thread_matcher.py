"""
Thread Reconstruction & Interview Event Deduplication Engine (v1.0 Production-Ready):
- Manages first-class conversation thread_id chains (Message-ID, In-Reply-To, References)
- Deduplicates interview events by separating round_name from status changes (Scheduled -> Confirmed -> Rescheduled)
- Maintains chronological event_sequence on thread timelines
- Normalizes round_type to strict RoundType Enum
"""

import logging
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview_intelligence.models import EmailTrainingData, InterviewEvent
from app.modules.interview_intelligence.schemas import (
    EmailCategory,
    EventStatus,
    NormalizedEmail,
    RoundType,
)

logger = logging.getLogger("interview_intelligence.thread_matcher")


class ThreadMatcher:
    """Handles conversation threading, event deduplication, and timeline sequence generation."""

    @classmethod
    async def resolve_or_create_thread_id(
        cls,
        session: AsyncSession,
        email_data: NormalizedEmail | dict[str, Any],
    ) -> uuid.UUID:
        """
        Resolves existing conversation thread_id from In-Reply-To or References.
        Generates a new UUID if starting a fresh email thread.
        """
        parent = await cls.find_thread_parent(session, email_data)
        if parent and parent.thread_id:
            return parent.thread_id
        if parent:
            # Backfill parent thread_id if missing
            parent.thread_id = parent.id
            session.add(parent)
            return parent.id

        return uuid.uuid4()

    @classmethod
    async def find_thread_parent(
        cls,
        session: AsyncSession,
        email_data: NormalizedEmail | dict[str, Any],
    ) -> EmailTrainingData | None:
        """
        Finds previous parent email in conversation thread via In-Reply-To or References headers.
        """
        in_reply_to = email_data.in_reply_to if isinstance(email_data, NormalizedEmail) else email_data.get("in_reply_to")
        references = email_data.references if isinstance(email_data, NormalizedEmail) else email_data.get("references", [])

        # 1. Direct RFC 822 In-Reply-To matching
        if in_reply_to:
            clean_parent = in_reply_to.strip("<>").strip()
            res = await session.execute(
                select(EmailTrainingData).where(
                    EmailTrainingData.message_id.ilike(f"%{clean_parent}%")
                ).order_by(desc(EmailTrainingData.created_at)).limit(1)
            )
            parent = res.scalar_one_or_none()
            if parent:
                return parent

        # 2. References list matching
        if references:
            for ref in references:
                clean_ref = ref.strip("<>").strip()
                res = await session.execute(
                    select(EmailTrainingData).where(
                        EmailTrainingData.message_id.ilike(f"%{clean_ref}%")
                    ).order_by(desc(EmailTrainingData.created_at)).limit(1)
                )
                parent = res.scalar_one_or_none()
                if parent:
                    return parent

        return None

    @classmethod
    async def match_and_deduplicate_event(
        cls,
        session: AsyncSession,
        email_record: EmailTrainingData,
        email_data: NormalizedEmail | dict[str, Any],
        category: str,
        company: str | None,
        role: str | None,
        round_name: str | None,
        round_type: str | None,
        status_value: str | None,
        meeting_link: str | None,
        deadline: str | None,
        thread_id: uuid.UUID | None = None,
        application_id: uuid.UUID | None = None,
    ) -> tuple[str, InterviewEvent | None]:
        """
        Smart deduplication & dynamic timeline generator:
        - Separates round extraction from status changes
        - Confirmed / Rescheduled / Cancelled update existing event on thread_id
        - New rounds create sequential InterviewEvent (event_sequence = chronological step)
        """
        resolved_thread_id = thread_id or email_record.thread_id

        # Find active events on this thread or application
        existing_events_query = select(InterviewEvent).order_by(desc(InterviewEvent.created_at))
        if resolved_thread_id:
            existing_events_query = existing_events_query.where(InterviewEvent.thread_id == resolved_thread_id)
        elif application_id:
            existing_events_query = existing_events_query.where(InterviewEvent.application_id == application_id)

        res = await session.execute(existing_events_query)
        existing_events = res.scalars().all()
        latest_event = existing_events[0] if existing_events else None

        final_round_type = round_type or cls._infer_round_type(category, round_name)
        final_round_name = round_name or cls._default_round_name(category)
        final_status = status_value or cls._default_status(category)

        # CASE 1: Confirmation of existing scheduled interview
        if (category == EmailCategory.INTERVIEW_CONFIRMATION.value or final_status == EventStatus.CONFIRMED.value) and latest_event:
            latest_event.status = EventStatus.CONFIRMED.value
            if meeting_link:
                latest_event.meeting_link = meeting_link
            latest_event.email_id = email_record.id
            if round_name and not latest_event.round_name:
                latest_event.round_name = round_name
                latest_event.round = round_name
            session.add(latest_event)
            return "updated_existing_event", latest_event

        # CASE 2: Reschedule of existing interview
        if (category == EmailCategory.INTERVIEW_RESCHEDULE.value or final_status == EventStatus.RESCHEDULED.value) and latest_event:
            latest_event.status = EventStatus.RESCHEDULED.value
            if meeting_link:
                latest_event.meeting_link = meeting_link
            latest_event.email_id = email_record.id
            session.add(latest_event)
            return "updated_existing_event", latest_event

        # CASE 3: Cancellation of interview
        if (category == EmailCategory.INTERVIEW_CANCELLED.value or final_status == EventStatus.CANCELLED.value) and latest_event:
            latest_event.status = EventStatus.CANCELLED.value
            latest_event.email_id = email_record.id
            session.add(latest_event)
            return "updated_existing_event", latest_event

        # CASE 4: Rejection notification
        if category == EmailCategory.REJECTION.value or final_status == EventStatus.REJECTED.value:
            if latest_event and latest_event.status != EventStatus.REJECTED.value:
                latest_event.status = "Closed"
                session.add(latest_event)

            rejection_event = InterviewEvent(
                id=uuid.uuid4(),
                thread_id=resolved_thread_id,
                application_id=application_id,
                email_id=email_record.id,
                event_type="rejection",
                event_sequence=len(existing_events) + 1,
                round_name="Application Closed",
                round_type=RoundType.REJECTION.value,
                round="Application Closed",
                status=EventStatus.REJECTED.value,
                recruiter=email_record.sender_name or email_record.sender_email,
                raw_json={"reason": "Candidate rejection notice received"},
            )
            session.add(rejection_event)
            return "recorded_rejection", rejection_event

        # CASE 5: New Dynamic Interview Round
        if category in (
            EmailCategory.INTERVIEW.value,
            EmailCategory.HR_SCREENING.value,
            EmailCategory.TECHNICAL_ASSESSMENT.value,
            EmailCategory.TAKE_HOME.value,
            EmailCategory.APPLICATION_UPDATE.value,
            EmailCategory.RECRUITER_FOLLOWUP.value,
        ):
            next_seq = (max(e.event_sequence for e in existing_events) + 1) if existing_events else 1

            new_event = InterviewEvent(
                id=uuid.uuid4(),
                thread_id=resolved_thread_id,
                application_id=application_id,
                email_id=email_record.id,
                event_type=category,
                event_sequence=next_seq,
                round_name=final_round_name,
                round_type=final_round_type,
                round=final_round_name,
                status=final_status,
                meeting_link=meeting_link,
                deadline=deadline,
                recruiter=email_record.sender_name or email_record.sender_email,
                raw_json={"category": category, "company": company, "role": role, "round_name": final_round_name},
            )
            session.add(new_event)
            return "created_new_interview_event", new_event

        return "categorized_only", None

    @staticmethod
    def _infer_round_type(category: str, round_name: str | None) -> str:
        """Infers normalized round_type while preserving dynamic round_name."""
        if round_name:
            rn_lower = round_name.lower()
            if any(k in rn_lower for k in ["hiring committee", "team match", "debrief"]):
                return RoundType.INTERNAL.value
            if any(k in rn_lower for k in ["bar raiser", "technical", "phone screen", "onsite", "loop", "coding"]):
                return RoundType.INTERVIEW.value
            if any(k in rn_lower for k in ["oa", "assessment", "hackerrank", "codesignal", "take-home"]):
                return RoundType.TECHNICAL_ASSESSMENT.value
            if any(k in rn_lower for k in ["recruiter", "hr"]):
                return RoundType.HR_SCREENING.value
            if any(k in rn_lower for k in ["offer"]):
                return RoundType.OFFER.value

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

    @staticmethod
    def _default_status(category: str) -> str:
        """Returns standard EventStatus for a given category."""
        if category == EmailCategory.INTERVIEW_CONFIRMATION.value:
            return EventStatus.CONFIRMED.value
        if category == EmailCategory.INTERVIEW_RESCHEDULE.value:
            return EventStatus.RESCHEDULED.value
        if category == EmailCategory.INTERVIEW_CANCELLED.value:
            return EventStatus.CANCELLED.value
        if category == EmailCategory.REJECTION.value:
            return EventStatus.REJECTED.value
        return EventStatus.SCHEDULED.value

    @staticmethod
    def _default_round_name(category: str) -> str:
        """Returns standard round title when email does not specify an exact company round name."""
        mapping = {
            EmailCategory.HR_SCREENING.value: "Recruiter Screen",
            EmailCategory.TECHNICAL_ASSESSMENT.value: "Online Assessment",
            EmailCategory.TAKE_HOME.value: "Take-Home Assignment",
            EmailCategory.INTERVIEW.value: "Technical Interview",
            EmailCategory.APPLICATION_UPDATE.value: "Application Update",
            EmailCategory.RECRUITER_FOLLOWUP.value: "Recruiter Outreach",
        }
        return mapping.get(category, "Interview Round")
