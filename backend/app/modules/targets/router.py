import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.targets import service
from app.modules.targets.schemas import (
    EmployeeTargetProgressResponse,
    TargetResponse,
    TargetSetRequest,
)
from app.modules.users.models import User

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("", response_model=list[TargetResponse])
async def list_targets(
    employee_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List targets: Admin sees all, Sub-Admin sees scoped, Employee sees their own."""
    return await service.get_targets(db, current_user, employee_id)


@router.post("", response_model=TargetResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def set_target(
    payload: TargetSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/Sub-Admin sets or updates target for an employee for a client."""
    target = await service.set_target(db, current_user, payload)
    targets = await service.get_targets(db, current_user, payload.employee_id)
    for t in targets:
        if t.client_id == payload.client_id:
            return t
    return TargetResponse.model_validate(target)


@router.post("/{target_id}/pause", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def pause_target_endpoint(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause an active target."""
    await service.pause_target(db, target_id, current_user)
    return {"message": "Target paused successfully"}


@router.post("/{target_id}/resume", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def resume_target_endpoint(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused target."""
    await service.resume_target(db, target_id, current_user)
    return {"message": "Target resumed successfully"}


@router.post("/{target_id}/end", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def end_target_endpoint(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """End a target."""
    await service.end_target(db, target_id, current_user)
    return {"message": "Target ended successfully"}


@router.delete("/{target_id}", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def delete_target_endpoint(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete target (allowed only before effective date)."""
    await service.delete_target(db, target_id, current_user)
    return {"message": "Target deleted successfully"}


@router.get("/progress", response_model=EmployeeTargetProgressResponse)
async def get_my_target_progress(
    employee_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get target progress breakdown and overall completion percentage."""
    target_emp_id = current_user.id
    if employee_id and current_user.role in ("admin", "sub_admin"):
        target_emp_id = employee_id

    return await service.get_employee_target_progress(db, target_emp_id)
