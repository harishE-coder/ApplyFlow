"""
Activity Log model.
Tracks all significant user actions from Day 1.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    # Actions: "login", "resume_uploaded", "application_submitted",
    #          "target_updated", "user_created", "client_created"
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ActivityLog {self.action} by user={self.user_id}>"
