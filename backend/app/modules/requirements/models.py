"""
Requirement model.
A Client (e.g. ABC Staffing) can have multiple job requirements for different target companies (e.g. TCS - Java Developer, Amazon - Frontend Engineer).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # Target company e.g. "TCS", "Infosys", "Amazon"
    role: Mapped[str] = mapped_column(
        String(150), nullable=False, index=True
    )  # e.g. "Java Developer", "Frontend Engineer"
    role_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g. "TCS-JAVA-01", "AMZ-FE-02"
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # "active", "closed", "on-hold"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    client: Mapped["Client"] = relationship(  # noqa: F821
        back_populates="requirements", lazy="selectin"
    )
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        back_populates="requirement", lazy="selectin"
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        back_populates="requirement", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Requirement {self.role_code}: {self.company} - {self.role}>"
