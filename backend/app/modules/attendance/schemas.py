import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AttendanceRecordResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    check_in: datetime
    check_out: datetime | None = None
    total_hours: str | None = None
    is_active: bool = False

    model_config = {"from_attributes": True}


class AdminAttendanceSummary(BaseModel):
    present_today: int
    checked_in: int
    checked_out: int
    working_now: int
    active_employees: list[dict] = []
