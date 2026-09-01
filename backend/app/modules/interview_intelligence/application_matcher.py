"""
Automatic Application Matcher for ATS Integration (v1.0 Production-Ready):
- Implements strict hierarchical company matching precedence:
  1. Groq extracted hiring company name
  2. Subject line search across active candidate applications
  3. Body text / signature company keywords
  4. Sender domain root (excluding 3rd-party ATS platforms: Greenhouse, Lever, Ashby, Workday)
- Synchronizes Application workflow state, current_round, and email snippets
"""

import logging
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import Application
from app.modules.interview_intelligence.schemas import EmailCategory

logger = logging.getLogger("interview_intelligence.application_matcher")

IGNORED_ATS_PLATFORMS = {
    "greenhouse", "lever", "workday", "ashby", "ashbyhq", "smartrecruiters",
    "workable", "workablemail", "bamboohr", "jobvite", "taleo", "icims",
    "hirevue", "testgorilla", "hackerrank", "codesignal", "codility", "coderpad",
    "calendly", "zoom", "google", "microsoft", "gmail", "outlook", "yahoo"
}


class ApplicationMatcher:
    """Matches recruitment emails to ApplyFlow Application records and transitions their workflow status."""

    @classmethod
    async def match_application(
        cls,
        session: AsyncSession,
        company: str | None,
        role: str | None = None,
        sender_domain: str | None = None,
        subject: str | None = None,
        body_text: str | None = None,
        client_id: Any = None,
    ) -> Application | None:
        """
        Finds the matching Application record in the database using hierarchical matching precedence:
        1. Groq Extracted Company (+ Role)
        2. Subject Line match against active applications
        3. Body text / signature match against active applications
        4. Sender domain root match (excluding third-party ATS platforms)
        """
        # 1. Groq Extracted Company + Role match
        if company and company.strip().lower() not in IGNORED_ATS_PLATFORMS:
            clean_company = company.strip()
            query = select(Application).where(
                Application.company.ilike(f"%{clean_company}%")
            )
            if client_id:
                query = query.where(Application.client_id == client_id)

            if role:
                clean_role = role.strip()
                role_query = query.where(Application.role.ilike(f"%{clean_role}%"))
                res = await session.execute(role_query.order_by(desc(Application.applied_date)).limit(1))
                app = res.scalar_one_or_none()
                if app:
                    return app

            # Company-only query
            res = await session.execute(query.order_by(desc(Application.applied_date)).limit(1))
            app = res.scalar_one_or_none()
            if app:
                return app

        # 2. Subject search across active applications
        if subject:
            res = await session.execute(
                select(Application).order_by(desc(Application.applied_date)).limit(100)
            )
            apps = res.scalars().all()
            for app in apps:
                if app.company and len(app.company) >= 3 and app.company.lower() in subject.lower():
                    return app

        # 3. Body text search across active applications
        if body_text:
            res = await session.execute(
                select(Application).order_by(desc(Application.applied_date)).limit(50)
            )
            apps = res.scalars().all()
            for app in apps:
                if app.company and len(app.company) >= 3 and app.company.lower() in body_text.lower():
                    return app

        # 4. Sender Domain heuristic match (ONLY if domain is NOT a 3rd-party ATS platform)
        if sender_domain and "." in sender_domain:
            domain_root = sender_domain.split(".")[0].strip().lower()
            if domain_root not in IGNORED_ATS_PLATFORMS and len(domain_root) >= 3:
                res = await session.execute(
                    select(Application)
                    .where(Application.company.ilike(f"%{domain_root}%"))
                    .order_by(desc(Application.applied_date))
                    .limit(1)
                )
                app = res.scalar_one_or_none()
                if app:
                    return app

        return None

    @classmethod
    async def sync_application_status(
        cls,
        session: AsyncSession,
        application: Application,
        category: str,
        round_name: str | None = None,
        meeting_link: str | None = None,
        email_preview: str | None = None,
    ) -> None:
        """Updates Application status, current_round, and email snippet on new events."""
        if category in (EmailCategory.INTERVIEW.value, EmailCategory.INTERVIEW_CONFIRMATION.value):
            application.status = "Interview Scheduled"
            if round_name:
                application.current_round = round_name
        elif category in (EmailCategory.TECHNICAL_ASSESSMENT.value, EmailCategory.TAKE_HOME.value):
            application.status = "Technical"
            if round_name:
                application.current_round = round_name
        elif category == EmailCategory.HR_SCREENING.value:
            application.status = "HR Screening"
            if round_name:
                application.current_round = round_name
        elif category == EmailCategory.REJECTION.value:
            application.status = "Rejected"
        elif category == EmailCategory.INTERVIEW_CANCELLED.value:
            application.status = "Hold"

        if email_preview:
            application.last_email_snippet = email_preview[:250]

        application.is_ai_processed = True
        session.add(application)
        logger.info(f"Updated Application {application.id} status to '{application.status}' (Round: '{application.current_round}')")
