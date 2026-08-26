"""
Client and EmployeeClient models.
A Client is our customer who takes recruitment services from Apply Flow (e.g. ABC Staffing, Talent Hub, NextHire).
Each client can have multiple job requirements for different companies.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    company_name: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, inactive, archived
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # For auto-assignment / hierarchy tracking
    managed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    client_users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="client", lazy="selectin", foreign_keys="User.client_id"
    )
    employee_assignments: Mapped[list["EmployeeClient"]] = relationship(
        back_populates="client", lazy="selectin", foreign_keys="EmployeeClient.client_id"
    )
    requirements: Mapped[list["Requirement"]] = relationship(  # noqa: F821
        back_populates="client", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Client {self.company_name}>"


class EmployeeClient(Base):
    """Many-to-many mapping: which employees work for which clients."""

    __tablename__ = "employee_clients"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "client_id", name="uq_employee_client"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )

    # Granular ownership fields
    is_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    employee: Mapped["User"] = relationship(  # noqa: F821
        back_populates="employee_assignments", lazy="selectin", foreign_keys=[employee_id]
    )
    client: Mapped["Client"] = relationship(
        back_populates="employee_assignments", lazy="selectin", foreign_keys=[client_id]
    )

    def __repr__(self) -> str:
        return f"<EmployeeClient emp={self.employee_id} client={self.client_id} active={self.active}>"
