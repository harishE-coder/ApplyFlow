from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.attendance import service
from app.modules.attendance.schemas import (
    AdminAttendanceSummary,
    AttendanceRecordResponse,
)
from app.modules.users.models import User
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("/status", response_model=AttendanceRecordResponse | None)
async def get_current_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get today's attendance status for the current employee."""
    record = await service.get_today_attendance(db, current_user.id)
    if not record:
        return None
    return AttendanceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        work_date=record.work_date,
        check_in=record.check_in,
        check_out=record.check_out,
        total_hours=record.total_hours,
        is_active=record.check_out is None,
    )


@router.post("/check-in", response_model=AttendanceRecordResponse)
async def check_in(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start employee daily work session."""
    return await service.check_in(db, current_user)


@router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """End employee daily work session."""
    return await service.check_out(db, current_user)


@router.get("/admin-summary", response_model=AdminAttendanceSummary, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_attendance_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin and Sub-Admin live attendance summary for today."""
    allowed_emp_ids = None
    if current_user.role == "sub_admin":
        from app.modules.users.service import get_sub_admin_employee_ids
        allowed_emp_ids = await get_sub_admin_employee_ids(db, current_user.id)
    return await service.get_admin_attendance_summary(db, allowed_employee_ids=allowed_emp_ids)
