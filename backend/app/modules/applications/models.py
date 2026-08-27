"""
Application, ApplicationEvent, and EmailIntake models.
Powers the AI Email Intake & Application Timeline system.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EmailIntake(Base):
    __tablename__ = "email_intake"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True, index=True
    )
    original_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="paste"
    )  # "paste", "eml", "pdf", "image"
    confidence: Mapped[int] = mapped_column(
        Integer, default=95
    )
    processed: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    uploader: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    client: Mapped["Client"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EmailIntake id={self.id} source={self.source_type} conf={self.confidence}>"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_apps_emp_applied", "employee_id", "applied_date"),
        Index("ix_apps_client_applied", "client_id", "applied_date"),
        Index("ix_apps_status_applied", "status", "applied_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id"), nullable=True, index=True
    )
    candidate_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )
    company: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    role: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requirements.id"), nullable=True, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Submitted", index=True
    )  # "Submitted", "Round 1", "Round 2", "Technical", "Manager", "HR", "Shortlisted", "Offer", "Rejected", "Hold", "Closed", "Archived"
    current_round: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default="Initial Application"
    )
    interview_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=95
    )
    last_email_snippet: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    is_ai_processed: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    applied_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True
    )

    # Relationships
    resume: Mapped["Resume | None"] = relationship(lazy="selectin")  # noqa: F821
    requirement: Mapped["Requirement | None"] = relationship(back_populates="applications", lazy="selectin")  # noqa: F821
    employee: Mapped["User"] = relationship(foreign_keys=[employee_id], lazy="selectin")  # noqa: F821
    client: Mapped["Client | None"] = relationship(lazy="selectin")  # noqa: F821
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApplicationEvent.created_at.asc()",
    )

    @property
    def display_candidate_name(self) -> str:
        if self.resume and self.resume.candidate_name:
            return self.resume.candidate_name
        return self.candidate_name or "Unknown Candidate"

    @property
    def display_company(self) -> str:
        if self.resume and self.resume.company:
            return self.resume.company
        return self.company or "Company"

    @property
    def display_role(self) -> str:
        if self.resume and self.resume.role:
            return self.resume.role
        return self.role or "Role"

    def __repr__(self) -> str:
        return f"<Application {self.id} status={self.status} round={self.current_round}>"


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "Submitted", "Round 1", "Round 2", "Technical", "Manager", "HR", "Shortlisted", "Offer", "Rejected", "Hold"
    round_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    event_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_intake.id"), nullable=True, index=True
    )
    raw_email: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    ai_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    confidence: Mapped[int] = mapped_column(
        Integer, default=90
    )
    interview_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="events", lazy="selectin")
    creator: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    email_intake: Mapped["EmailIntake"] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<ApplicationEvent id={self.id} event={self.event_type} round={self.round_name}>"
