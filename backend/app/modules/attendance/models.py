from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.core.database import Base
from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.modules.users.models import User


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date(), index=True
    )
    check_in: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    check_out: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_hours: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # Relationships
    employee: Mapped[User] = relationship(lazy="selectin")

    def __repr__(self) -> str:
        return f"<Attendance employee={self.employee_id} date={self.work_date} check_in={self.check_in}>"
