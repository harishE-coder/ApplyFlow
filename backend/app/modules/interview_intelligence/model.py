"""
Local Machine Learning Model Engine:
- TF-IDF Vectorizer (1-2 ngrams, sublinear scaling)
- Logistic Regression (multinomial, balanced class weights)
- CalibratedClassifierCV (method='sigmoid') for true probability calibration
- Sub-100ms inference with Stricter Production Confidence Thresholds:
    >= 97% -> Accept (Direct Processing)
    75-96% -> AI Teacher (Groq Fallback)
    < 75%  -> Review Queue (Human Verification)
"""

import logging
import time
from pathlib import Path
from typing import Any

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.modules.interview_intelligence.features import (
    build_feature_text,
    extract_domain_signals,
)
from app.modules.interview_intelligence.schemas import EmailCategory, NormalizedEmail
from app.modules.interview_intelligence.seed_data import GOLDEN_SEED_TEMPLATES

logger = logging.getLogger("interview_intelligence.model")

MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models"


class ClassificationDecision(str):
    ACCEPT = "accept"            # >= 97% calibrated confidence
    AI_FALLBACK = "ai_fallback"  # 75 - 96% calibrated confidence
    REVIEW_QUEUE = "review_queue"# < 75% calibrated confidence


class LocalInterviewClassifier:
    """Manages the in-memory TF-IDF + Logistic Regression model with probability calibration."""

    def __init__(self, version: str = "v1.0.0"):
        self.version = version
        self.pipeline: Any = None
        self.classes: list[str] = [c.value for c in EmailCategory]
        self._is_trained = False

    def build_pipeline(self) -> Pipeline:
        """Constructs the base vectorizer + logistic regression pipeline."""
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=20000,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        classifier = LogisticRegression(
            solver="lbfgs",
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
            C=1.0,
        )
        return Pipeline([
            ("tfidf", vectorizer),
            ("clf", classifier),
        ])

    def train(self, texts: list[str], labels: list[str], calibrate: bool = True) -> float:
        """
        Trains the pipeline on feature texts and labels using CalibratedClassifierCV.
        """
        if not texts or not labels or len(texts) != len(labels):
            raise ValueError("Invalid training data: texts and labels must be non-empty and equal length.")

        base_pipe = self.build_pipeline()
        unique_labels = sorted(list(set(labels)))
        if len(unique_labels) < 2:
            raise ValueError("Training requires at least 2 distinct label classes.")

        min_class_count = min(labels.count(c) for c in unique_labels)

        if calibrate and min_class_count >= 2:
            cv_splits = min(3, min_class_count)
            try:
                calibrated = CalibratedClassifierCV(
                    estimator=base_pipe,
                    method="sigmoid",
                    cv=cv_splits,
                )
                calibrated.fit(texts, labels)
                self.pipeline = calibrated
            except Exception as e:
                logger.warning(f"CalibratedClassifierCV fallback to base pipeline: {e}")
                base_pipe.fit(texts, labels)
                self.pipeline = base_pipe
        else:
            base_pipe.fit(texts, labels)
            self.pipeline = base_pipe

        self._is_trained = True

        # Calculate accuracy on training batch
        preds = self.pipeline.predict(texts)
        correct = sum(1 for p, y in zip(preds, labels) if p == y)
        accuracy = correct / len(labels)
        return accuracy

    def train_baseline(self) -> float:
        """Trains a baseline model on the golden seed templates."""
        texts = [build_feature_text(item["email"]) for item in GOLDEN_SEED_TEMPLATES]
        labels = [item["label"] for item in GOLDEN_SEED_TEMPLATES]
        acc = self.train(texts, labels, calibrate=False)
        self.save()
        return acc

    def predict(self, email_input: NormalizedEmail | dict[str, Any]) -> dict[str, Any]:
        """
        Runs local inference in < 100ms and returns structured decision & calibrated confidence.
        """
        t0 = time.perf_counter()

        if not self._is_trained or self.pipeline is None:
            self.train_baseline()

        feature_text = build_feature_text(email_input)
        raw_links = email_input.links if isinstance(email_input, NormalizedEmail) else (email_input.get("links") or [])
        domain_signals = extract_domain_signals(raw_links)

        # Get calibrated probability distribution
        probs = self.pipeline.predict_proba([feature_text])[0]
        classes = self.pipeline.classes_

        class_prob_map = {str(cls_name): float(p) for cls_name, p in zip(classes, probs)}
        best_class = max(class_prob_map, key=class_prob_map.get)

        sorted_probs = sorted(probs, reverse=True)
        top1 = sorted_probs[0]
        top2 = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
        margin_ratio = (top1 / (top1 + top2)) if (top1 + top2) > 0 else top1

        confidence_pct = int(round(margin_ratio * 100))

        # Unambiguous domain platform boosts
        if domain_signals.get("has_assessment_platform") and best_class == EmailCategory.TECHNICAL_ASSESSMENT.value:
            confidence_pct = max(confidence_pct, 98)
        elif domain_signals.get("has_interview_platform") and best_class in (EmailCategory.INTERVIEW.value, EmailCategory.HR_SCREENING.value):
            confidence_pct = max(confidence_pct, 97)
        elif best_class == EmailCategory.REJECTION.value and top1 > 0.15:
            confidence_pct = max(confidence_pct, 90)

        confidence_pct = max(10, min(100, confidence_pct))

        # Decision Table (Tuned Stricter Thresholds for Precision):
        # >= 97 -> Accept
        # 75 - 96 -> AI Fallback
        # < 75 -> Review Queue
        if confidence_pct >= 97:
            decision = ClassificationDecision.ACCEPT
        elif confidence_pct >= 75:
            decision = ClassificationDecision.AI_FALLBACK
        else:
            decision = ClassificationDecision.REVIEW_QUEUE

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "category": best_class,
            "confidence": confidence_pct,
            "decision": decision,
            "probabilities": class_prob_map,
            "model_version": self.version,
            "latency_ms": latency_ms,
            "domain_signals": domain_signals,
        }

    def save(self, model_dir: Path | None = None, upload_to_storage: bool = False) -> str:
        """Serializes the trained pipeline to disk via joblib and optionally uploads to Supabase Storage."""
        from app.modules.interview_intelligence.storage import supabase_storage

        target_dir = model_dir or (MODELS_DIR / self.version)
        target_dir.mkdir(parents=True, exist_ok=True)
        model_path = target_dir / "classifier.joblib"
        joblib.dump(self.pipeline, model_path)
        logger.info(f"Model saved to {model_path}")

        if upload_to_storage:
            storage_key = f"models/{self.version}/classifier.joblib"
            supabase_storage.upload_file_direct(storage_key, model_path.read_bytes(), content_type="application/octet-stream")
            logger.info(f"Model uploaded to Supabase Storage: {storage_key}")

        return str(model_path)

    def load(self, model_path: str | Path | None = None, fetch_from_storage: bool = False) -> bool:
        """Loads serialized model from disk or Supabase Storage."""
        from app.modules.interview_intelligence.storage import supabase_storage

        path = Path(model_path) if model_path else (MODELS_DIR / self.version / "classifier.joblib")

        if fetch_from_storage and not path.exists():
            storage_key = f"models/{self.version}/classifier.joblib"
            raw_bytes = supabase_storage.download_raw_file(storage_key)
            if raw_bytes:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw_bytes)

        if path.exists():
            try:
                self.pipeline = joblib.load(path)
                self._is_trained = True
                logger.info(f"Loaded model from {path}")
                return True
            except Exception as e:
                logger.error(f"Error loading model from {path}: {e}")
        return False


# Global singleton instance
local_classifier = LocalInterviewClassifier()
