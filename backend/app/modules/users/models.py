from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.clients.models import Client, EmployeeClient


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_email_active", "email", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "admin", "sub_admin", "employee", "client"
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # "active", "inactive", "archived"

    # For client-role users: links to their company
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )

    # For auto-assignment / hierarchy tracking
    managed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    client: Mapped[Client | None] = relationship(
        back_populates="client_users", lazy="selectin", foreign_keys=[client_id]
    )
    employee_assignments: Mapped[list[EmployeeClient]] = relationship(
        back_populates="employee", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin", foreign_keys="EmployeeClient.employee_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.name} ({self.role})>"


class SubAdminAssignment(Base):
    """
    Super Admin delegates clients/employees to Sub-Admin.
    """
    __tablename__ = "sub_admin_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sub_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sub_admin: Mapped[User] = relationship(foreign_keys=[sub_admin_id], lazy="selectin")
    employee: Mapped[User | None] = relationship(foreign_keys=[employee_id], lazy="selectin")
    client: Mapped[Client | None] = relationship(lazy="selectin")
