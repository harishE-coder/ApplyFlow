"""
Dataset Exporter for Interview Intelligence Pipeline.
Supports structured dataset hierarchy in Supabase Storage:
- datasets/seed/{version}/train.jsonl: Initial bootstrap dataset
- datasets/golden/golden.jsonl: Frozen evaluation benchmark
- datasets/human_verified/train.jsonl: High-precision human corrections
- datasets/production_exports/{version}/train.jsonl: Retraining dataset with quality gating
"""

import json
import logging
import random
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview_intelligence.features import build_feature_text
from app.modules.interview_intelligence.models import EmailTrainingData
from app.modules.interview_intelligence.storage import supabase_storage

logger = logging.getLogger("interview_intelligence.export")


class DatasetExporter:
    """Exports structured training and evaluation datasets to Supabase Storage."""

    @classmethod
    async def export_from_db(
        cls,
        session: AsyncSession,
        version: str = "v1.0.0",
        val_split: float = 0.2,
        seed: int = 42,
        human_only: bool = True,
    ) -> dict[str, Any]:
        """
        Exports labeled emails from database and Supabase Storage to train.jsonl & validation.jsonl.
        Quality gating: by default includes only human-verified/approved labels to prevent drift.
        """
        query = select(EmailTrainingData).where(
            EmailTrainingData.category.is_not(None),
            EmailTrainingData.category != "",
        )
        if human_only:
            query = query.where(EmailTrainingData.source.in_(["human", "seed_golden"]))

        query = query.order_by(EmailTrainingData.created_at.asc())
        result = await session.execute(query)
        records = result.scalars().all()

        if not records:
            logger.warning("No verified training records found in database. Using seed dataset.")
            return cls.export_seed_dataset(version=version)

        dataset_entries: list[dict[str, Any]] = []
        golden_entries: list[dict[str, Any]] = []
        class_counts: dict[str, int] = {}

        for rec in records:
            cat = str(rec.category).strip()
            email_payload = supabase_storage.download_email(rec.storage_key)
            if not email_payload:
                email_payload = {
                    "subject": rec.subject or "",
                    "sender_domain": rec.sender_domain or "",
                    "sender_email": rec.sender_email or "",
                    "body": rec.body_preview or "",
                    "links": [],
                    "attachment_names": [a.get("name") for a in (rec.attachment_metadata or []) if isinstance(a, dict)],
                }

            feature_text = build_feature_text(email_payload)
            entry = {
                "text": feature_text,
                "label": cat,
                "confidence": rec.confidence,
                "source": rec.source,
                "source_version": rec.classification_source_version,
                "email_hash": rec.email_hash,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            }

            dataset_entries.append(entry)
            class_counts[cat] = class_counts.get(cat, 0) + 1

            if rec.source == "human":
                golden_entries.append(entry)

        rng = random.Random(seed)
        shuffled = list(dataset_entries)
        rng.shuffle(shuffled)

        val_size = int(len(shuffled) * val_split)
        val_entries = shuffled[:val_size]
        train_entries = shuffled[val_size:] if val_size < len(shuffled) else shuffled

        train_jsonl = "\n".join(json.dumps(e, ensure_ascii=False) for e in train_entries).encode("utf-8")
        val_jsonl = "\n".join(json.dumps(e, ensure_ascii=False) for e in val_entries).encode("utf-8")
        golden_jsonl = "\n".join(json.dumps(e, ensure_ascii=False) for e in golden_entries).encode("utf-8")

        # Save to Supabase Storage production_exports & human_verified paths
        train_key = f"datasets/production_exports/{version}/train.jsonl"
        val_key = f"datasets/production_exports/{version}/validation.jsonl"
        golden_key = "datasets/golden/golden.jsonl"
        human_key = "datasets/human_verified/train.jsonl"

        supabase_storage.upload_file_direct(train_key, train_jsonl, content_type="application/x-ndjson")
        supabase_storage.upload_file_direct(val_key, val_jsonl, content_type="application/x-ndjson")
        if golden_entries:
            supabase_storage.upload_file_direct(golden_key, golden_jsonl, content_type="application/x-ndjson")
            supabase_storage.upload_file_direct(human_key, golden_jsonl, content_type="application/x-ndjson")

        return {
            "version": version,
            "total_samples": len(dataset_entries),
            "train_samples": len(train_entries),
            "validation_samples": len(val_entries),
            "golden_samples": len(golden_entries),
            "class_distribution": class_counts,
            "paths": {
                "train": train_key,
                "validation": val_key,
                "golden": golden_key if golden_entries else None,
                "human_verified": human_key if golden_entries else None,
            },
        }

    @classmethod
    def export_seed_dataset(cls, version: str = "v1.0.0") -> dict[str, Any]:
        """Generates and exports the golden baseline template dataset across all 13 categories."""
        from app.modules.interview_intelligence.seed_data import GOLDEN_SEED_TEMPLATES

        train_entries = []
        class_counts = {}

        for item in GOLDEN_SEED_TEMPLATES:
            text = build_feature_text(item["email"])
            cat = item["label"]
            entry = {
                "text": text,
                "label": cat,
                "confidence": 100,
                "source": "seed_golden",
                "email_hash": f"seed_{str(abs(hash(text)))[:16]}",
            }
            train_entries.append(entry)
            class_counts[cat] = class_counts.get(cat, 0) + 1

        train_jsonl = "\n".join(json.dumps(e, ensure_ascii=False) for e in train_entries).encode("utf-8")
        train_key = f"datasets/seed/{version}/train.jsonl"
        golden_key = "datasets/golden/golden.jsonl"

        supabase_storage.upload_file_direct(train_key, train_jsonl, content_type="application/x-ndjson")
        supabase_storage.upload_file_direct(golden_key, train_jsonl, content_type="application/x-ndjson")

        return {
            "version": version,
            "total_samples": len(train_entries),
            "train_samples": len(train_entries),
            "validation_samples": 0,
            "golden_samples": len(train_entries),
            "class_distribution": class_counts,
            "paths": {"train": train_key, "validation": None, "golden": golden_key},
        }
