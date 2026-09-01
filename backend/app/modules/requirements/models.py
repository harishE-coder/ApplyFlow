from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.applications.models import Application
    from app.modules.clients.models import Client
    from app.modules.resumes.models import Resume
    from app.modules.users.models import User


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # Target hiring company e.g. "TCS", "Infosys", "Amazon"
    role: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )  # e.g. "Java Developer", "Frontend Engineer"
    job_title: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # Alias/canonical job title
    role_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g. "TCS-JAVA-01", "AMZ-FE-02"
    job_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # External link to job posting (e.g. careers portal)
    priority: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False
    )  # "High", "Medium", "Low"
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Recruiter guidance notes
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # "active", "done", "archived", "closed"

    # Global vs Individual Recruiter Assignment
    assignment_type: Mapped[str] = mapped_column(
        String(20), default="all", nullable=False
    )  # "all" (Global for all employees), "individual"
    assigned_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    client: Mapped[Client] = relationship(
        back_populates="requirements", lazy="selectin"
    )
    creator: Mapped[User | None] = relationship(
        foreign_keys=[created_by], lazy="selectin"
    )
    completer: Mapped[User | None] = relationship(
        foreign_keys=[completed_by], lazy="selectin"
    )
    assigned_employee: Mapped[User | None] = relationship(
        foreign_keys=[assigned_employee_id], lazy="selectin"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="requirement", passive_deletes=True, lazy="selectin"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="requirement", passive_deletes=True, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Requirement {self.company} - {self.role} ({self.status})>"
