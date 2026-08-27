import uuid
from datetime import date, datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.modules.users.models import User
from app.modules.attendance.models import Attendance
from app.modules.attendance.schemas import AttendanceRecordResponse, AdminAttendanceSummary
from app.modules.activity_logs.models import ActivityLog


from app.core.cache import invalidate_dashboard_cache

def _format_duration(start: datetime, end: datetime) -> str:
    if start.tzinfo is not None and end.tzinfo is None:
        start = start.replace(tzinfo=None)
    elif start.tzinfo is None and end.tzinfo is not None:
        end = end.replace(tzinfo=None)
    diff = end - start
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"



async def get_today_attendance(db: AsyncSession, employee_id: uuid.UUID) -> Attendance | None:
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.work_date == today,
        ).order_by(Attendance.check_in.desc())
    )
    return result.scalars().first()


async def check_in(db: AsyncSession, user: User) -> AttendanceRecordResponse:
    today = date.today()
    existing = await get_today_attendance(db, user.id)
    if existing and existing.check_out is None:
        return AttendanceRecordResponse(
            id=existing.id,
            employee_id=existing.employee_id,
            work_date=existing.work_date,
            check_in=existing.check_in,
            check_out=existing.check_out,
            total_hours=existing.total_hours,
            is_active=True,
        )

    now = datetime.now(timezone.utc)
    record = Attendance(
        employee_id=user.id,
        work_date=today,
        check_in=now,
    )
    db.add(record)
    await db.flush()

    db.add(
        ActivityLog(
            user_id=user.id,
            action="attendance_check_in",
            details={"check_in": now.isoformat()},
        )
    )
    await db.flush()
    invalidate_dashboard_cache()

    return AttendanceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        work_date=record.work_date,
        check_in=record.check_in,
        check_out=None,
        total_hours=None,
        is_active=True,
    )


async def check_out(db: AsyncSession, user: User) -> AttendanceRecordResponse:
    record = await get_today_attendance(db, user.id)
    if not record or record.check_out is not None:
        raise HTTPException(status_code=400, detail="No active work session to check out from.")

    now = datetime.now(timezone.utc)
    record.check_out = now
    record.total_hours = _format_duration(record.check_in, now)
    await db.flush()

    db.add(
        ActivityLog(
            user_id=user.id,
            action="attendance_check_out",
            details={
                "check_out": now.isoformat(),
                "total_hours": record.total_hours,
            },
        )
    )
    await db.flush()
    invalidate_dashboard_cache()

    return AttendanceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        work_date=record.work_date,
        check_in=record.check_in,
        check_out=record.check_out,
        total_hours=record.total_hours,
        is_active=False,
    )


async def get_admin_attendance_summary(db: AsyncSession) -> AdminAttendanceSummary:
    today = date.today()
    result = await db.execute(
        select(Attendance, User.name)
        .join(User, Attendance.employee_id == User.id)
        .where(Attendance.work_date == today)
    )
    rows = result.all()

    present_ids = set()
    checked_in_count = 0
    checked_out_count = 0
    working_now_count = 0
    employee_list = []

    for att, uname in rows:
        present_ids.add(att.employee_id)
        is_working = att.check_out is None
        if is_working:
            working_now_count += 1
            checked_in_count += 1
        else:
            checked_out_count += 1

        employee_list.append({
            "employee_id": str(att.employee_id),
            "employee_name": uname,
            "check_in": att.check_in.strftime("%I:%M %p") if att.check_in else "-",
            "check_out": att.check_out.strftime("%I:%M %p") if att.check_out else "-",
            "total_hours": att.total_hours or "-",
            "is_working_now": is_working,
        })

    return AdminAttendanceSummary(
        present_today=len(present_ids),
        checked_in=checked_in_count,
        checked_out=checked_out_count,
        working_now=working_now_count,
        active_employees=employee_list,
    )
