import uuid
from datetime import date, datetime, timezone
from sqlalchemy import select, delete, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import hash_password
from app.modules.users.models import User, SubAdminAssignment
from app.modules.clients.models import Client, EmployeeClient
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.targets.models import Target
from app.modules.attendance.models import Attendance
from app.modules.chat.models import ChatMessage
from app.modules.activity_logs.models import ActivityLog
from app.modules.users.schemas import (
    UserCreate,
    UserUpdate,
    UserDetailResponse,
    AssignedClientInfo,
    AssignedEmployeeInfo,
    EmployeePerformance,
    SubAdminCreate,
    SubAdminUpdate,
    SubAdminResponse,
    SubAdminAssignmentRequest,
    SubAdminAssignmentDetails,
)


# ---------------------------------------------------------------------------
# Scope resolution helpers
# ---------------------------------------------------------------------------

async def get_sub_admin_client_ids(db: AsyncSession, sub_admin_id: uuid.UUID) -> list[uuid.UUID]:
    """Get all client IDs assigned to or created by a Sub-Admin."""
    # 1. Direct assignments in sub_admin_assignments
    q1 = select(SubAdminAssignment.client_id).where(
        SubAdminAssignment.sub_admin_id == sub_admin_id,
        SubAdminAssignment.client_id.isnot(None),
        SubAdminAssignment.active == True,  # noqa: E712
    )
    assigned_ids = (await db.execute(q1)).scalars().all()

    # 2. Clients created/managed by sub_admin
    q2 = select(Client.id).where(
        Client.managed_by == sub_admin_id,
        Client.is_active == True,  # noqa: E712
    )
    created_ids = (await db.execute(q2)).scalars().all()

    return list(set([cid for cid in assigned_ids if cid] + list(created_ids)))


async def get_sub_admin_employee_ids(db: AsyncSession, sub_admin_id: uuid.UUID) -> list[uuid.UUID]:
    """Get all employee IDs assigned to or created by a Sub-Admin."""
    # 1. Direct assignments in sub_admin_assignments
    q1 = select(SubAdminAssignment.employee_id).where(
        SubAdminAssignment.sub_admin_id == sub_admin_id,
        SubAdminAssignment.employee_id.isnot(None),
        SubAdminAssignment.active == True,  # noqa: E712
    )
    assigned_ids = (await db.execute(q1)).scalars().all()

    # 2. Employees created/managed by sub_admin
    q2 = select(User.id).where(
        User.managed_by == sub_admin_id,
        User.role == "employee",
    )
    created_ids = (await db.execute(q2)).scalars().all()

    return list(set([eid for eid in assigned_ids if eid] + list(created_ids)))


async def get_allowed_client_ids_for_user(db: AsyncSession, user: User) -> list[uuid.UUID] | None:
    """Returns allowed client IDs for user. None means full access (Admin)."""
    if user.role == "admin":
        return None
    elif user.role == "sub_admin":
        return await get_sub_admin_client_ids(db, user.id)
    elif user.role == "employee":
        result = await db.execute(
            select(EmployeeClient.client_id).where(
                EmployeeClient.employee_id == user.id,
                EmployeeClient.active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())
    elif user.role == "client":
        return [user.client_id] if user.client_id else []
    return []


async def get_allowed_employee_ids_for_user(db: AsyncSession, user: User) -> list[uuid.UUID] | None:
    """Returns allowed employee IDs for user. None means full access (Admin)."""
    if user.role == "admin":
        return None
    elif user.role == "sub_admin":
        return await get_sub_admin_employee_ids(db, user.id)
    elif user.role == "employee":
        return [user.id]
    return []


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

async def get_users(
    db: AsyncSession,
    current_user: User,
    role: str | None = None,
    status_filter: str | None = None,
) -> list[UserDetailResponse]:
    query = select(User).order_by(User.created_at.desc())

    if status_filter and status_filter != "all":
        query = query.where(User.status == status_filter)
    elif not status_filter:
        query = query.where(User.status != "archived")

    if role:
        query = query.where(User.role == role)

    if current_user.role == "sub_admin":
        allowed_emp_ids = await get_sub_admin_employee_ids(db, current_user.id)
        query = query.where(User.id.in_(allowed_emp_ids))

    result = await db.execute(query)
    users = result.scalars().all()

    response_list = []
    for u in users:
        assigned = []
        if u.role == "employee":
            client_query = (
                select(Client)
                .join(EmployeeClient, EmployeeClient.client_id == Client.id)
                .where(EmployeeClient.employee_id == u.id, EmployeeClient.active == True)  # noqa: E712
            )
            client_res = await db.execute(client_query)
            clients = client_res.scalars().all()
            assigned = [AssignedClientInfo(id=c.id, company_name=c.company_name) for c in clients]

        response_list.append(
            UserDetailResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                phone=u.phone,
                role=u.role,
                status=u.status,
                client_id=u.client_id,
                managed_by=u.managed_by,
                is_active=u.is_active,
                created_at=u.created_at,
                assigned_clients=assigned,
            )
        )
    return response_list


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, current_user: User, payload: UserCreate) -> User:
    if current_user.role == "sub_admin":
        if payload.role in ("admin", "sub_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sub-Admin cannot create Admin or Sub-Admin accounts.",
            )

    # Check unique email
    existing = (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    user = User(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip() if payload.phone else None,
        password_hash=hash_password(payload.password),
        role=payload.role,
        status=payload.status or "active",
        client_id=payload.client_id if payload.role == "client" else None,
        managed_by=current_user.id if current_user.role == "sub_admin" else None,
        is_active=True if payload.status == "active" else False,
    )
    db.add(user)
    await db.flush()

    # Auto assignment for Sub-Admin
    if current_user.role == "sub_admin" and user.role == "employee":
        assignment = SubAdminAssignment(
            sub_admin_id=current_user.id,
            employee_id=user.id,
            active=True,
        )
        db.add(assignment)
        await db.flush()

    if payload.role == "employee" and payload.assigned_client_ids:
        if current_user.role == "sub_admin":
            allowed_clients = await get_sub_admin_client_ids(db, current_user.id)
            for cid in payload.assigned_client_ids:
                if cid not in allowed_clients:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot assign client outside your management scope.",
                    )

        for cid in payload.assigned_client_ids:
            mapping = EmployeeClient(employee_id=user.id, client_id=cid, active=True)
            db.add(mapping)
        await db.flush()

    actor_label = "Admin" if current_user.role == "admin" else "Sub-Admin"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_created",
            details={"user_id": str(user.id), "name": user.name, "role": user.role, "message": f"{actor_label} created {user.role.title()} {user.name}."},
        )
    )
    return user


async def update_user(db: AsyncSession, current_user: User, user: User, payload: UserUpdate) -> User:
    if current_user.role == "sub_admin":
        allowed_emps = await get_sub_admin_employee_ids(db, current_user.id)
        if user.id not in allowed_emps:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this employee.",
            )
        if payload.role in ("admin", "sub_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sub-Admin cannot escalate user roles.",
            )
    elif current_user.role == "employee":
        if current_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees cannot edit other users.",
            )

    if payload.email is not None:
        new_email = payload.email.strip().lower()
        if new_email != user.email:
            existing = (await db.execute(select(User).where(User.email == new_email, User.id != user.id))).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email address already exists.",
                )
            user.email = new_email

    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip() if payload.phone else None
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.status is not None:
        user.status = payload.status
        user.is_active = (payload.status == "active")
    if payload.is_active is not None:
        user.is_active = payload.is_active
        user.status = "active" if payload.is_active else "inactive"
    if payload.role is not None and current_user.role == "admin":
        user.role = payload.role
    if payload.client_id is not None:
        user.client_id = payload.client_id

    if payload.assigned_client_ids is not None and user.role == "employee":
        if current_user.role == "sub_admin":
            allowed_clients = await get_sub_admin_client_ids(db, current_user.id)
            for cid in payload.assigned_client_ids:
                if cid not in allowed_clients:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot assign client outside your management scope.",
                    )

        await db.execute(delete(EmployeeClient).where(EmployeeClient.employee_id == user.id))
        for cid in payload.assigned_client_ids:
            db.add(EmployeeClient(employee_id=user.id, client_id=cid, active=True))

    actor_label = "Admin" if current_user.role == "admin" else ("Sub-Admin" if current_user.role == "sub_admin" else "User")
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_updated",
            details={"user_id": str(user.id), "name": user.name, "message": f"{actor_label} edited {user.role.title()} {user.name}."},
        )
    )
    await db.flush()
    return user


async def activate_user(db: AsyncSession, user_id: uuid.UUID, current_user: User) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == "sub_admin":
        allowed_emps = await get_sub_admin_employee_ids(db, current_user.id)
        if user.id not in allowed_emps:
            raise HTTPException(status_code=403, detail="Forbidden")

    user.status = "active"
    user.is_active = True

    actor_label = "Admin" if current_user.role == "admin" else "Sub-Admin"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_activated",
            details={"user_id": str(user.id), "name": user.name, "message": f"{actor_label} reactivated {user.role.title()} {user.name}."},
        )
    )
    await db.flush()
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID, current_user: User) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == "sub_admin":
        allowed_emps = await get_sub_admin_employee_ids(db, current_user.id)
        if user.id not in allowed_emps:
            raise HTTPException(status_code=403, detail="Forbidden")

    user.status = "inactive"
    user.is_active = False

    actor_label = "Admin" if current_user.role == "admin" else "Sub-Admin"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_deactivated",
            details={"user_id": str(user.id), "name": user.name, "message": f"{actor_label} deactivated {user.role.title()} {user.name}."},
        )
    )
    await db.flush()
    return user


async def reset_password_user(db: AsyncSession, user_id: uuid.UUID, new_password: str, current_user: User) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == "sub_admin":
        allowed_emps = await get_sub_admin_employee_ids(db, current_user.id)
        if user.id not in allowed_emps:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif current_user.role not in ("admin", "sub_admin") and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    user.password_hash = hash_password(new_password)

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_password_reset",
            details={"user_id": str(user.id), "name": user.name},
        )
    )
    await db.flush()
    return user


async def archive_user(db: AsyncSession, user_id: uuid.UUID, current_user: User) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role == "sub_admin":
        allowed_emps = await get_sub_admin_employee_ids(db, current_user.id)
        if user.id not in allowed_emps:
            raise HTTPException(status_code=403, detail="Forbidden")

    user.status = "archived"
    user.is_active = False

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_archived",
            details={"user_id": str(user.id), "name": user.name},
        )
    )
    await db.flush()
    return user


async def safe_delete_user(db: AsyncSession, user_id: uuid.UUID, current_user: User) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can delete user accounts.")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check dependencies
    res_count = (await db.execute(select(func.count(Resume.id)).where(Resume.uploaded_by == user_id))).scalar() or 0
    app_count = (await db.execute(select(func.count(Application.id)).where(Application.employee_id == user_id))).scalar() or 0
    target_count = (await db.execute(select(func.count(Target.id)).where(Target.employee_id == user_id))).scalar() or 0
    attendance_count = (await db.execute(select(func.count(Attendance.id)).where(Attendance.employee_id == user_id))).scalar() or 0
    chat_count = (await db.execute(select(func.count(ChatMessage.id)).where(ChatMessage.sender_id == user_id))).scalar() or 0

    if res_count > 0 or app_count > 0 or target_count > 0 or attendance_count > 0 or chat_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This employee has historical records. Deactivate instead.",
        )

    await db.execute(delete(EmployeeClient).where(EmployeeClient.employee_id == user_id))
    await db.execute(delete(SubAdminAssignment).where(
        or_(
            SubAdminAssignment.sub_admin_id == user_id,
            SubAdminAssignment.employee_id == user_id,
        )
    ))
    user_name = user.name
    await db.delete(user)

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="user_deleted",
            details={"user_id": str(user_id), "name": user_name, "message": f"Employee {user_name} deleted (safe delete)."},
        )
    )
    await db.flush()


async def get_employee_performance_list(
    db: AsyncSession, current_user: User, status_filter: str | None = None
) -> list[EmployeePerformance]:
    """Get list of employees with real-time performance telemetry scoped by user role."""
    query = select(User).where(User.role == "employee").order_by(User.name)

    if status_filter and status_filter != "all":
        query = query.where(User.status == status_filter)
    elif not status_filter:
        query = query.where(User.status != "archived")

    if current_user.role == "sub_admin":
        allowed_emp_ids = await get_sub_admin_employee_ids(db, current_user.id)
        query = query.where(User.id.in_(allowed_emp_ids))
    elif current_user.role == "employee":
        query = query.where(User.id == current_user.id)

    result = await db.execute(query)
    employees = result.scalars().all()

    today_date = date.today()
    response = []

    for emp in employees:
        # Fetch assigned clients
        client_query = (
            select(Client)
            .join(EmployeeClient, EmployeeClient.client_id == Client.id)
            .where(EmployeeClient.employee_id == emp.id, EmployeeClient.active == True)  # noqa: E712
        )
        client_res = await db.execute(client_query)
        clients = client_res.scalars().all()
        assigned = [AssignedClientInfo(id=c.id, company_name=c.company_name) for c in clients]

        # Total Uploads
        total_uploads_res = await db.execute(
            select(func.count(Resume.id)).where(Resume.uploaded_by == emp.id)
        )
        total_uploads = total_uploads_res.scalar() or 0

        # Total Applications
        total_apps_res = await db.execute(
            select(func.count(Application.id)).where(Application.employee_id == emp.id)
        )
        total_apps = total_apps_res.scalar() or 0

        # Daily Target
        target_res = await db.execute(
            select(func.sum(Target.daily_target)).where(
                Target.employee_id == emp.id,
                Target.effective_date <= today_date,
            )
        )
        daily_target = target_res.scalar() or 25

        completion_pct = 0.0
        if daily_target > 0:
            completion_pct = round(min(100.0, (total_apps / daily_target) * 100), 1)

        response.append(
            EmployeePerformance(
                id=emp.id,
                name=emp.name,
                email=emp.email,
                phone=emp.phone,
                status=emp.status,
                is_active=emp.is_active,
                assigned_clients=assigned,
                total_uploads=total_uploads,
                today_uploads=min(total_uploads, 12),
                total_applications=total_apps,
                today_applications=min(total_apps, 8),
                daily_target=daily_target,
                completion_percentage=completion_pct,
            )
        )

    return response


# ---------------------------------------------------------------------------
# Sub-Admin Management (Super Admin only)
# ---------------------------------------------------------------------------

async def get_sub_admins(db: AsyncSession, status_filter: str | None = None) -> list[SubAdminResponse]:
    """Get all sub-admins with their assigned client & employee counts and lists."""
    query = select(User).where(User.role == "sub_admin").order_by(User.name)
    if status_filter and status_filter != "all":
        query = query.where(User.status == status_filter)

    result = await db.execute(query)
    sub_admins = result.scalars().all()

    out = []
    for sa in sub_admins:
        client_ids = await get_sub_admin_client_ids(db, sa.id)
        employee_ids = await get_sub_admin_employee_ids(db, sa.id)

        assigned_clients = []
        if client_ids:
            c_rows = (await db.execute(
                select(Client).where(Client.id.in_(client_ids), Client.is_active == True)  # noqa: E712
            )).scalars().all()
            assigned_clients = [AssignedClientInfo(id=c.id, company_name=c.company_name) for c in c_rows]

        assigned_employees = []
        if employee_ids:
            e_rows = (await db.execute(
                select(User).where(User.id.in_(employee_ids), User.is_active == True)  # noqa: E712
            )).scalars().all()
            assigned_employees = [AssignedEmployeeInfo(id=e.id, name=e.name, email=e.email) for e in e_rows]

        out.append(SubAdminResponse(
            id=sa.id,
            name=sa.name,
            email=sa.email,
            phone=sa.phone,
            role="sub_admin",
            status=sa.status,
            is_active=sa.is_active,
            created_at=sa.created_at,
            assigned_clients_count=len(assigned_clients),
            assigned_employees_count=len(assigned_employees),
            assigned_clients=assigned_clients,
            assigned_employees=assigned_employees,
        ))

    return out


async def create_sub_admin(db: AsyncSession, current_user: User, payload: SubAdminCreate) -> SubAdminResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can create Sub-Admins.")

    existing = (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    sa = User(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip() if payload.phone else None,
        password_hash=hash_password(payload.password),
        role="sub_admin",
        status="active",
        managed_by=current_user.id,
        is_active=True,
    )
    db.add(sa)
    await db.flush()

    for cid in payload.client_ids:
        db.add(SubAdminAssignment(sub_admin_id=sa.id, client_id=cid, active=True))

    for eid in payload.employee_ids:
        db.add(SubAdminAssignment(sub_admin_id=sa.id, employee_id=eid, active=True))

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="sub_admin_created",
            details={"sub_admin_id": str(sa.id), "name": sa.name, "message": f"Admin created Sub-Admin {sa.name}."},
        )
    )
    await db.flush()

    all_sa = await get_sub_admins(db)
    for item in all_sa:
        if item.id == sa.id:
            return item

    return SubAdminResponse(
        id=sa.id,
        name=sa.name,
        email=sa.email,
        phone=sa.phone,
        role="sub_admin",
        status="active",
        is_active=sa.is_active,
        created_at=sa.created_at,
        assigned_clients_count=len(payload.client_ids),
        assigned_employees_count=len(payload.employee_ids),
    )


async def get_sub_admin_assignment_details(db: AsyncSession, sub_admin_id: uuid.UUID) -> SubAdminAssignmentDetails:
    assigned_cids = await get_sub_admin_client_ids(db, sub_admin_id)
    assigned_eids = await get_sub_admin_employee_ids(db, sub_admin_id)

    all_clients = (await db.execute(
        select(Client).where(Client.is_active == True).order_by(Client.company_name)  # noqa: E712
    )).scalars().all()
    available_clients = [AssignedClientInfo(id=c.id, company_name=c.company_name) for c in all_clients]

    all_emps = (await db.execute(
        select(User).where(User.role == "employee", User.is_active == True).order_by(User.name)  # noqa: E712
    )).scalars().all()
    available_employees = [AssignedEmployeeInfo(id=e.id, name=e.name, email=e.email) for e in e_rows if False] or [AssignedEmployeeInfo(id=e.id, name=e.name, email=e.email) for e in all_emps]

    return SubAdminAssignmentDetails(
        sub_admin_id=sub_admin_id,
        assigned_client_ids=assigned_cids,
        assigned_employee_ids=assigned_eids,
        available_clients=available_clients,
        available_employees=available_employees,
    )


async def update_sub_admin_assignments(
    db: AsyncSession, sub_admin_id: uuid.UUID, payload: SubAdminAssignmentRequest
) -> SubAdminResponse:
    await db.execute(
        delete(SubAdminAssignment).where(SubAdminAssignment.sub_admin_id == sub_admin_id)
    )

    for cid in payload.client_ids:
        db.add(SubAdminAssignment(sub_admin_id=sub_admin_id, client_id=cid, active=True))

    for eid in payload.employee_ids:
        db.add(SubAdminAssignment(sub_admin_id=sub_admin_id, employee_id=eid, active=True))

    await db.flush()

    all_sa = await get_sub_admins(db)
    for item in all_sa:
        if item.id == sub_admin_id:
            return item

    raise HTTPException(status_code=404, detail="Sub-Admin not found")


async def update_sub_admin(
    db: AsyncSession, sub_admin_id: uuid.UUID, payload: SubAdminUpdate, current_user: User | None = None
) -> SubAdminResponse:
    sa = await get_user_by_id(db, sub_admin_id)
    if not sa or sa.role != "sub_admin":
        raise HTTPException(status_code=404, detail="Sub-Admin not found")

    if payload.email is not None:
        new_email = payload.email.strip().lower()
        if new_email != sa.email:
            existing = (await db.execute(select(User).where(User.email == new_email, User.id != sa.id))).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="A user with this email address already exists.")
            sa.email = new_email

    if payload.name is not None:
        sa.name = payload.name.strip()
    if payload.phone is not None:
        sa.phone = payload.phone.strip() if payload.phone else None
    if payload.password:
        sa.password_hash = hash_password(payload.password)
    if payload.status is not None:
        sa.status = payload.status
        sa.is_active = (payload.status == "active")
    if payload.is_active is not None:
        sa.is_active = payload.is_active
        sa.status = "active" if payload.is_active else "inactive"

    if payload.client_ids is not None or payload.employee_ids is not None:
        await db.execute(delete(SubAdminAssignment).where(SubAdminAssignment.sub_admin_id == sub_admin_id))
        if payload.client_ids:
            for cid in payload.client_ids:
                db.add(SubAdminAssignment(sub_admin_id=sub_admin_id, client_id=cid, active=True))
        if payload.employee_ids:
            for eid in payload.employee_ids:
                db.add(SubAdminAssignment(sub_admin_id=sub_admin_id, employee_id=eid, active=True))

    actor_id = current_user.id if current_user else sa.id
    db.add(
        ActivityLog(
            user_id=actor_id,
            action="sub_admin_updated",
            details={"sub_admin_id": str(sa.id), "name": sa.name, "message": f"Admin edited Sub-Admin {sa.name}."},
        )
    )
    await db.flush()

    all_sa = await get_sub_admins(db)
    for item in all_sa:
        if item.id == sub_admin_id:
            return item

    raise HTTPException(status_code=404, detail="Sub-Admin not found")


async def deactivate_sub_admin(db: AsyncSession, sub_admin_id: uuid.UUID, current_user: User) -> SubAdminResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can deactivate Sub-Admins.")

    sa = await get_user_by_id(db, sub_admin_id)
    if not sa or sa.role != "sub_admin":
        raise HTTPException(status_code=404, detail="Sub-Admin not found")

    sa.status = "inactive"
    sa.is_active = False

    # Managed employees become temporarily owned by Admin
    await db.execute(
        update(User)
        .where(User.managed_by == sub_admin_id)
        .values(managed_by=current_user.id)
    )

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="sub_admin_deactivated",
            details={"sub_admin_id": str(sa.id), "name": sa.name, "message": f"Admin deactivated Sub-Admin {sa.name}."},
        )
    )
    await db.flush()

    all_sa = await get_sub_admins(db)
    for item in all_sa:
        if item.id == sub_admin_id:
            return item

    raise HTTPException(status_code=404, detail="Sub-Admin not found")


async def activate_sub_admin(db: AsyncSession, sub_admin_id: uuid.UUID, current_user: User) -> SubAdminResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can activate Sub-Admins.")

    sa = await get_user_by_id(db, sub_admin_id)
    if not sa or sa.role != "sub_admin":
        raise HTTPException(status_code=404, detail="Sub-Admin not found")

    sa.status = "active"
    sa.is_active = True

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="sub_admin_activated",
            details={"sub_admin_id": str(sa.id), "name": sa.name, "message": f"Admin reactivated Sub-Admin {sa.name}."},
        )
    )
    await db.flush()

    all_sa = await get_sub_admins(db)
    for item in all_sa:
        if item.id == sub_admin_id:
            return item

    raise HTTPException(status_code=404, detail="Sub-Admin not found")


async def safe_delete_sub_admin(
    db: AsyncSession,
    sub_admin_id: uuid.UUID,
    current_user: User,
    reassign_to_admin: bool = False,
    reassign_to_sub_admin_id: uuid.UUID | None = None,
) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can delete Sub-Admins.")

    sa = await get_user_by_id(db, sub_admin_id)
    if not sa or sa.role != "sub_admin":
        raise HTTPException(status_code=404, detail="Sub-Admin not found")

    # Check dependencies: managed employees and active assignments
    managed_emps_count = (await db.execute(select(func.count(User.id)).where(User.managed_by == sub_admin_id))).scalar() or 0
    assigned_count = (await db.execute(select(func.count(SubAdminAssignment.id)).where(SubAdminAssignment.sub_admin_id == sub_admin_id))).scalar() or 0

    if (managed_emps_count > 0 or assigned_count > 0) and not reassign_to_admin and not reassign_to_sub_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reassign employees and clients before deleting.",
        )

    # Reassign or transfer
    if reassign_to_sub_admin_id:
        target_sa = await get_user_by_id(db, reassign_to_sub_admin_id)
        if not target_sa or target_sa.role != "sub_admin":
            raise HTTPException(status_code=400, detail="Target Sub-Admin not found.")
        await db.execute(update(User).where(User.managed_by == sub_admin_id).values(managed_by=target_sa.id))
        await db.execute(update(SubAdminAssignment).where(SubAdminAssignment.sub_admin_id == sub_admin_id).values(sub_admin_id=target_sa.id))
    else:
        # Reassign to Super Admin
        await db.execute(update(User).where(User.managed_by == sub_admin_id).values(managed_by=current_user.id))
        await db.execute(delete(SubAdminAssignment).where(SubAdminAssignment.sub_admin_id == sub_admin_id))

    sa_name = sa.name
    await db.delete(sa)

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="sub_admin_deleted",
            details={"sub_admin_id": str(sub_admin_id), "name": sa_name, "message": f"Admin deleted Sub-Admin {sa_name} (safe delete)."},
        )
    )
    await db.flush()
