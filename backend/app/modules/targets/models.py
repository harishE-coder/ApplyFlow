"""
Target model.
Admin sets daily targets per employee per client.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Target(Base):
    __tablename__ = "targets"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "client_id", "effective_date",
            name="uq_target_employee_client_date",
        ),
        Index("ix_targets_emp_status", "employee_id", "status"),
        Index("ix_targets_client_status", "client_id", "status"),
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
    daily_target: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )  # active, paused, ended
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    employee: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    client: Mapped["Client"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Target employee={self.employee_id} client={self.client_id} target={self.daily_target} status={self.status}>"
