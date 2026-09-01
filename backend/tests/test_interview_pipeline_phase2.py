"""
Comprehensive Test Suite for Phase 2: Local ML Feature Pipeline & Confidence Engine
Tests:
1. Multi-signal feature extraction with explicit binary signals (HAS_ICS=1, HAS_MEETING_LINK=1, HAS_DEADLINE=1).
2. Domain signal heuristics (assessment, interview, scheduling, ATS).
3. Quality-gated dataset exporter (generating train.jsonl, validation.jsonl, golden.jsonl, human_verified).
4. TF-IDF + Logistic Regression model training with CalibratedClassifierCV and sub-100ms inference.
5. Production confidence calibration with stricter precision thresholds (Accept >= 97, AI Fallback 75-96, Review Queue < 75).
"""

import pytest
from app.modules.interview_intelligence.export_dataset import DatasetExporter
from app.modules.interview_intelligence.features import (
    build_feature_text,
    extract_domain_signals,
)
from app.modules.interview_intelligence.model import (
    ClassificationDecision,
    LocalInterviewClassifier,
)
from app.modules.interview_intelligence.schemas import EmailCategory, NormalizedEmail


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def test_feature_builder_and_binary_signals():
    email = NormalizedEmail(
        subject="Technical Assessment Invitation - Snowflake",
        sender_email="recruiting@snowflake.com",
        sender_domain="snowflake.com",
        links=["https://hackerrank.com/test/123", "https://calendly.com/snowflake/tech"],
        attachment_names=["instructions.pdf", "invite.ics"],
        body="Please complete the HackerRank coding challenge within 48 hours.",
    )

    feature_text = build_feature_text(email)
    assert "SUBJECT: Technical Assessment Invitation - Snowflake" in feature_text
    assert "SENDER_DOMAIN: snowflake.com" in feature_text
    assert "SENDER_EMAIL: recruiting@snowflake.com" in feature_text
    assert "hackerrank.com" in feature_text
    assert "calendly.com" in feature_text
    assert "HAS_ICS=1" in feature_text
    assert "HAS_MEETING_LINK=1" in feature_text
    assert "HAS_DEADLINE=1" in feature_text
    assert "BODY: Please complete the HackerRank" in feature_text

    signals = extract_domain_signals(email.links)
    assert signals["has_assessment_platform"] is True
    assert signals["has_scheduling_platform"] is True


def test_dataset_exporter_seed_generation():
    export_res = DatasetExporter.export_seed_dataset(version="v1.0.0-test")
    assert export_res["total_samples"] >= 13
    assert export_res["train_samples"] >= 13
    assert "datasets/seed/v1.0.0-test/train.jsonl" in export_res["paths"]["train"]
    assert export_res["paths"]["golden"] == "datasets/golden/golden.jsonl"
    assert len(export_res["class_distribution"]) >= 10


def test_local_model_training_and_serialization(tmp_path):
    classifier = LocalInterviewClassifier(version="v1.0.0-test")

    # 1. Train baseline
    accuracy = classifier.train_baseline()
    assert accuracy > 0.85
    assert classifier._is_trained is True

    # 2. Save model to temp dir
    saved_path = classifier.save(model_dir=tmp_path)
    assert "classifier.joblib" in saved_path

    # 3. Reload into fresh instance
    new_classifier = LocalInterviewClassifier(version="v1.0.0-test")
    assert new_classifier._is_trained is False
    loaded = new_classifier.load(model_path=saved_path)
    assert loaded is True
    assert new_classifier._is_trained is True


def test_sub_100ms_prediction_and_decision_engine():
    classifier = LocalInterviewClassifier(version="v1.0.0-test")
    classifier.train_baseline()

    # Case A: High-confidence technical assessment with HackerRank link
    assessment_email = NormalizedEmail(
        subject="Snowflake Online Technical Assessment - HackerRank",
        sender_email="evaluations@hackerrank.com",
        sender_domain="hackerrank.com",
        links=["https://hackerrank.com/tests/snowflake-oa"],
        attachment_names=[],
        body="You have been invited to complete a timed coding challenge on HackerRank within 48 hours.",
    )
    res_a = classifier.predict(assessment_email)
    assert res_a["category"] == EmailCategory.TECHNICAL_ASSESSMENT.value
    assert res_a["confidence"] >= 97
    assert res_a["decision"] == ClassificationDecision.ACCEPT
    assert res_a["latency_ms"] < 100.0  # Performance requirement

    # Case B: Technical interview invite with Zoom & invite.ics
    interview_email = NormalizedEmail(
        subject="Interview Schedule: Amazon SDE II Technical Round 1",
        sender_email="recruiting@amazon.jobs",
        sender_domain="amazon.jobs",
        links=["https://amazon.zoom.us/j/999111"],
        attachment_names=["invite.ics", "guide.pdf"],
        body="We would like to invite you for your 60-minute technical coding interview on Zoom.",
    )
    res_b = classifier.predict(interview_email)
    assert res_b["category"] in (EmailCategory.INTERVIEW.value, EmailCategory.HR_SCREENING.value)
    assert res_b["confidence"] >= 97
    assert res_b["decision"] == ClassificationDecision.ACCEPT
    assert res_b["latency_ms"] < 100.0

    # Case C: Rejection email
    rejection_email = NormalizedEmail(
        subject="Your application to Netflix",
        sender_email="talent@netflix.com",
        sender_domain="netflix.com",
        links=[],
        attachment_names=[],
        body="Thank you for interviewing. After consideration, we have decided to move forward with other candidates.",
    )
    res_c = classifier.predict(rejection_email)
    assert res_c["category"] == EmailCategory.REJECTION.value
    assert res_c["latency_ms"] < 100.0


def test_confidence_escalation_decision_logic():
    classifier = LocalInterviewClassifier(version="v1.0.0-test")
    classifier.train_baseline()

    # Ambiguous short email without strong headers
    ambiguous_email = NormalizedEmail(
        subject="Quick question",
        sender_email="someone@gmail.com",
        sender_domain="gmail.com",
        links=[],
        attachment_names=[],
        body="Hey, let's talk later.",
    )
    res = classifier.predict(ambiguous_email)
    # Ambiguous email should have lower confidence (< 97) and trigger AI fallback or review queue
    assert res["decision"] in (ClassificationDecision.AI_FALLBACK, ClassificationDecision.REVIEW_QUEUE)
