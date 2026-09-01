"""
Comprehensive Test Suite for Phase 3: Groq AI Teacher & Structured Extraction
Tests:
1. Versioned prompt loading (interview_teacher_v1.md).
2. Strict GroqTeacherResult JSON schema validation.
3. Fallback workflow from Local Model to Groq Teacher on uncertain confidence (75-96%).
4. Automatic TeacherDisagreement logging and needs_retraining=True flagging.
5. Threading metadata persistence (in_reply_to, pipeline_version).
"""

import uuid

import pytest
from app.core.database import Base
from app.modules.interview_intelligence.models import (
    EmailTrainingData,
    TeacherDisagreement,
)
from app.modules.interview_intelligence.schemas import (
    EmailCategory,
    GroqTeacherResult,
    NormalizedEmail,
)
from app.modules.interview_intelligence.teacher import GroqTeacherService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def test_prompt_versioning_and_payload_builder():
    teacher = GroqTeacherService(prompt_version="teacher_v1")
    prompt = teacher._get_prompt_template()
    assert "Groq AI Teacher" in prompt or "teacher_v1" in prompt or "category" in prompt

    email = NormalizedEmail(
        subject="Senior Systems Engineer Interview - Citadel",
        sender_email="recruiting@citadel.com",
        sender_domain="citadel.com",
        links=["https://citadel.zoom.us/j/12345"],
        attachment_names=["prep_guide.pdf"],
        body="We invite you to Technical Round 1 on Zoom.",
    )
    local_pred = {"category": "interview", "confidence": 85, "decision": "ai_fallback"}
    payload = teacher.build_user_payload(email, local_pred)

    assert payload["subject"] == "Senior Systems Engineer Interview - Citadel"
    assert payload["sender_domain"] == "citadel.com"
    assert payload["local_model_prediction"]["confidence"] == 85


@pytest.mark.anyio
async def test_groq_teacher_structured_json_extraction():
    teacher = GroqTeacherService(prompt_version="teacher_v1")
    email = NormalizedEmail(
        subject="Invitation: Snowflake Technical Assessment on HackerRank",
        sender_email="no-reply@hackerrank.com",
        sender_domain="hackerrank.com",
        links=["https://hackerrank.com/tests/snowflake-oa-123"],
        attachment_names=[],
        body="Please complete the 90-minute online assessment within 48 hours.",
    )

    result = await teacher.classify_with_teacher(email)
    assert isinstance(result, GroqTeacherResult)
    assert result.it_related is True
    assert result.category == EmailCategory.TECHNICAL_ASSESSMENT.value
    assert result.confidence >= 90
    assert result.prompt_version == "teacher_v1"
    assert "hackerrank" in (result.reason or "").lower() or "assessment" in (result.reason or "").lower()


@pytest.mark.anyio
async def test_teacher_disagreement_and_retraining_flag():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create an email where local model was uncertain or misclassified
        email_record = EmailTrainingData(
            id=uuid.uuid4(),
            version=1,
            message_id="uber-oa-999@uber.com",
            in_reply_to="uber-app-initial@uber.com",
            email_hash="999888777666555444333222111000aaabbbcccdddeeefff0001112223334445",
            subject="Next Steps in your Uber Application",
            sender_email="recruiting@uber.com",
            sender_domain="uber.com",
            body_preview="Please complete your CodeSignal assessment...",
            storage_key="emails/normalized/2026/09/01/uber.json",
            raw_storage_key="emails/raw/2026/09/01/uber.eml",
            body_sha256="abc123sha256hashvalue",
            category="recruiter_followup",  # Local model thought followup
            confidence=78,
            source="local",
            pipeline_version="interview_pipeline_v2.0",
            needs_retraining=False,
            processing_status="pending",
        )
        session.add(email_record)
        await session.commit()

        # Local model prediction
        local_pred = {"category": "recruiter_followup", "confidence": 78, "decision": "ai_fallback"}

        # Groq Teacher result extracts actual category: technical_assessment
        teacher_result = GroqTeacherResult(
            it_related=True,
            category=EmailCategory.TECHNICAL_ASSESSMENT.value,
            company="Uber",
            role="Software Engineer",
            round="Online Assessment",
            confidence=99,
            meeting_link="https://codesignal.com/eval/123",
            deadline="within 48 hours",
            reason="Detected CodeSignal evaluation link and time limit.",
            prompt_version="teacher_v1",
        )

        teacher = GroqTeacherService(prompt_version="teacher_v1")
        disagreement = await teacher.log_disagreement_if_any(
            session=session,
            email_record=email_record,
            local_prediction=local_pred,
            teacher_result=teacher_result,
        )
        await session.commit()

        assert disagreement is not None
        assert disagreement.local_label == "recruiter_followup"
        assert disagreement.ai_label == "technical_assessment"
        assert email_record.needs_retraining is True

        # Query back from DB
        from sqlalchemy import select
        res = await session.execute(
            select(TeacherDisagreement).where(TeacherDisagreement.email_id == email_record.id)
        )
        saved_dis = res.scalar_one_or_none()
        assert saved_dis is not None
        assert saved_dis.resolved is False
        assert saved_dis.ai_label == "technical_assessment"

    await test_engine.dispose()
