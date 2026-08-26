import uuid
from datetime import date, datetime
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.targets.models import Target
from app.modules.applications.models import Application
from app.modules.resumes.models import Resume
from app.modules.activity_logs.models import ActivityLog
from app.modules.targets.schemas import (
    TargetSetRequest,
    TargetResponse,
    ClientTargetProgress,
    EmployeeTargetProgressResponse,
)
from app.modules.users.service import get_sub_admin_client_ids, get_sub_admin_employee_ids


async def set_target(
    db: AsyncSession, current_user: User, payload: TargetSetRequest
) -> Target:
    if current_user.role == "sub_admin":
        allowed_cids = await get_sub_admin_client_ids(db, current_user.id)
        allowed_eids = await get_sub_admin_employee_ids(db, current_user.id)
        if payload.client_id not in allowed_cids or payload.employee_id not in allowed_eids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot set targets for resources outside your management scope.",
            )

    today = date.today()
    result = await db.execute(
        select(Target).where(
            Target.employee_id == payload.employee_id,
            Target.client_id == payload.client_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.daily_target = payload.daily_target
        existing.status = payload.status or "active"
        existing.effective_date = today
        target = existing
    else:
        target = Target(
            employee_id=payload.employee_id,
            client_id=payload.client_id,
            daily_target=payload.daily_target,
            status=payload.status or "active",
            effective_date=today,
        )
        db.add(target)

    await db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="target_updated",
            details={
                "employee_id": str(payload.employee_id),
                "client_id": str(payload.client_id),
                "daily_target": payload.daily_target,
            },
        )
    )

    return target


async def get_targets(
    db: AsyncSession, current_user: User, employee_id: uuid.UUID | None = None
) -> list[TargetResponse]:
    query = (
        select(Target, User.name, Client.company_name)
        .join(User, Target.employee_id == User.id)
        .join(Client, Target.client_id == Client.id)
    )

    if current_user.role == "sub_admin":
        allowed_cids = await get_sub_admin_client_ids(db, current_user.id)
        allowed_eids = await get_sub_admin_employee_ids(db, current_user.id)
        query = query.where(Target.client_id.in_(allowed_cids), Target.employee_id.in_(allowed_eids))
        if employee_id:
            query = query.where(Target.employee_id == employee_id)
    elif current_user.role == "employee":
        query = query.where(Target.employee_id == current_user.id)
    elif employee_id and current_user.role == "admin":
        query = query.where(Target.employee_id == employee_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        TargetResponse(
            id=t.id,
            employee_id=t.employee_id,
            employee_name=emp_name,
            client_id=t.client_id,
            client_name=client_name,
            daily_target=t.daily_target,
            status=t.status or "active",
            effective_date=t.effective_date,
        )
        for t, emp_name, client_name in rows
    ]


async def pause_target(db: AsyncSession, target_id: uuid.UUID, current_user: User) -> Target:
    target = (await db.execute(select(Target).where(Target.id == target_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target.status = "paused"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="target_paused",
            details={"target_id": str(target_id)},
        )
    )
    await db.flush()
    return target


async def resume_target(db: AsyncSession, target_id: uuid.UUID, current_user: User) -> Target:
    target = (await db.execute(select(Target).where(Target.id == target_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target.status = "active"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="target_resumed",
            details={"target_id": str(target_id)},
        )
    )
    await db.flush()
    return target


async def end_target(db: AsyncSession, target_id: uuid.UUID, current_user: User) -> Target:
    target = (await db.execute(select(Target).where(Target.id == target_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    target.status = "ended"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="target_ended",
            details={"target_id": str(target_id)},
        )
    )
    await db.flush()
    return target


async def delete_target(db: AsyncSession, target_id: uuid.UUID, current_user: User) -> None:
    target = (await db.execute(select(Target).where(Target.id == target_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    today = date.today()
    if target.effective_date < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete targets that are already past effective date. End or pause the target instead.",
        )

    await db.delete(target)
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="target_deleted",
            details={"target_id": str(target_id)},
        )
    )
    await db.flush()


async def get_employee_target_progress(
    db: AsyncSession, employee_id: uuid.UUID
) -> EmployeeTargetProgressResponse:
    t_query = (
        select(Target, Client.company_name)
        .join(Client, Target.client_id == Client.id)
        .where(Target.employee_id == employee_id, Target.status == "active")
    )
    t_result = await db.execute(t_query)
    targets = t_result.all()

    client_progress = []
    total_target = 0
    total_achieved = 0

    for target, client_name in targets:
        achieved_q = select(func.count(Application.id)).where(
            Application.employee_id == employee_id,
            Application.client_id == target.client_id,
        )
        achieved = (await db.execute(achieved_q)).scalar() or 0

        completion_pct = 0.0
        if target.daily_target > 0:
            completion_pct = round((achieved / target.daily_target) * 100, 1)

        client_progress.append(
            ClientTargetProgress(
                client_id=target.client_id,
                client_name=client_name,
                daily_target=target.daily_target,
                achieved_count=achieved,
                completion_percentage=completion_pct,
            )
        )
        total_target += target.daily_target
        total_achieved += achieved

    overall_pct = 0.0
    if total_target > 0:
        overall_pct = round((total_achieved / total_target) * 100, 1)

    return EmployeeTargetProgressResponse(
        total_target=total_target,
        total_achieved=total_achieved,
        overall_percentage=overall_pct,
        client_breakdown=client_progress,
    )
