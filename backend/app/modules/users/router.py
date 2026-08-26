import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.users.models import User
from app.modules.users.schemas import (
    UserCreate,
    UserUpdate,
    ResetPasswordRequest,
    UserDetailResponse,
    EmployeePerformance,
    SubAdminCreate,
    SubAdminUpdate,
    SubAdminResponse,
    SubAdminAssignmentRequest,
    SubAdminAssignmentDetails,
)
from app.modules.users import service

router = APIRouter(prefix="/api", tags=["users"])


# ---------------------------------------------------------------------------
# Users / Employees Management (Admin + Sub-Admin Scoped)
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserDetailResponse], dependencies=[Depends(require_role("admin", "sub_admin"))])
async def list_users(
    role: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users (Admin: all, Sub-Admin: scoped employees only, with status filter)."""
    return await service.get_users(db, current_user=current_user, role=role, status_filter=status_filter)


@router.post("/users", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.post("/employees", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create user (Admin: any role, Sub-Admin: employees only auto-assigned)."""
    user = await service.create_user(db, current_user=current_user, payload=payload)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user.id:
            return u
    return UserDetailResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.get("/employees/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found or outside your management scope")


@router.put("/users/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin", "employee"))])
@router.patch("/users/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin", "employee"))])
@router.put("/employees/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.patch("/employees/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await service.update_user(db, current_user=current_user, user=user, payload=payload)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    return UserDetailResponse.model_validate(user)


@router.patch("/employees/{user_id}/status", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def update_employee_status(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update employee status (active / inactive / archived)."""
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await service.update_user(db, current_user=current_user, user=user, payload=payload)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    return UserDetailResponse.model_validate(user)


@router.post("/users/{user_id}/activate", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.post("/employees/{user_id}/activate", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def activate_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate user account."""
    await service.activate_user(db, user_id, current_user)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/users/{user_id}/deactivate", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.post("/employees/{user_id}/deactivate", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def deactivate_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate user account: blocks login, preserves historical records."""
    await service.deactivate_user(db, user_id, current_user)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")


@router.post("/users/{user_id}/reset-password", dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.post("/employees/{user_id}/reset-password", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def reset_password_endpoint(
    user_id: uuid.UUID,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset user password."""
    await service.reset_password_user(db, user_id, payload.new_password, current_user)
    return {"message": "Password reset successfully"}


@router.post("/users/{user_id}/archive", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.post("/employees/{user_id}/archive", response_model=UserDetailResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def archive_user_endpoint(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive user account: hides from default active views."""
    await service.archive_user(db, user_id, current_user)
    users = await service.get_users(db, current_user=current_user, status_filter="all")
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")


@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
@router.delete("/employees/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Safe delete user (Admin only). Fails if historical resumes, applications, targets, attendance, or chat exist."""
    await service.safe_delete_user(db, user_id, current_user)
    return {"message": "User deleted successfully"}


@router.get("/employees", response_model=list[EmployeePerformance], dependencies=[Depends(require_role("admin", "sub_admin"))])
async def list_employees(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recruiters with performance metrics (Admin: all, Sub-Admin: scoped)."""
    return await service.get_employee_performance_list(db, current_user=current_user, status_filter=status_filter)


# ---------------------------------------------------------------------------
# Sub-Admin Management (Super Admin Only)
# ---------------------------------------------------------------------------

@router.get("/sub-admins", response_model=list[SubAdminResponse], dependencies=[Depends(require_role("admin"))])
async def list_sub_admins(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List all Sub-Admins with assigned resource counts (Super Admin only)."""
    return await service.get_sub_admins(db, status_filter=status_filter)


@router.post("/sub-admins", response_model=SubAdminResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
async def create_sub_admin(
    payload: SubAdminCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Sub-Admin with assigned clients and employees (Super Admin only)."""
    return await service.create_sub_admin(db, current_user=current_user, payload=payload)


@router.get("/sub-admins/{sub_admin_id}/assignments", response_model=SubAdminAssignmentDetails, dependencies=[Depends(require_role("admin"))])
async def get_sub_admin_assignments(
    sub_admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get assigned and available resources for a Sub-Admin."""
    return await service.get_sub_admin_assignment_details(db, sub_admin_id)


@router.put("/sub-admins/{sub_admin_id}/assignments", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
@router.post("/sub-admins/{sub_admin_id}/assignments", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
async def update_sub_admin_assignments(
    sub_admin_id: uuid.UUID,
    payload: SubAdminAssignmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update assigned clients and employees for a Sub-Admin."""
    return await service.update_sub_admin_assignments(db, sub_admin_id, payload)


@router.put("/sub-admins/{sub_admin_id}", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
@router.patch("/sub-admins/{sub_admin_id}", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
async def update_sub_admin_profile(
    sub_admin_id: uuid.UUID,
    payload: SubAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update Sub-Admin profile details."""
    return await service.update_sub_admin(db, sub_admin_id, payload, current_user=current_user)


@router.post("/sub-admins/{sub_admin_id}/deactivate", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
async def deactivate_sub_admin_endpoint(
    sub_admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate Sub-Admin: blocks login, managed employees reassigned to Admin."""
    return await service.deactivate_sub_admin(db, sub_admin_id, current_user=current_user)


@router.post("/sub-admins/{sub_admin_id}/activate", response_model=SubAdminResponse, dependencies=[Depends(require_role("admin"))])
async def activate_sub_admin_endpoint(
    sub_admin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate Sub-Admin."""
    return await service.activate_sub_admin(db, sub_admin_id, current_user=current_user)


@router.delete("/sub-admins/{sub_admin_id}", dependencies=[Depends(require_role("admin"))])
async def delete_sub_admin_endpoint(
    sub_admin_id: uuid.UUID,
    reassign_to_admin: bool = Query(False),
    reassign_to_sub_admin_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Safe delete Sub-Admin: requires reassignment if managed employees/clients exist."""
    await service.safe_delete_sub_admin(
        db,
        sub_admin_id,
        current_user=current_user,
        reassign_to_admin=reassign_to_admin,
        reassign_to_sub_admin_id=reassign_to_sub_admin_id,
    )
    return {"message": "Sub-Admin deleted successfully"}
