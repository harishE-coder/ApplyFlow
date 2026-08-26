import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.activity_logs.models import ActivityLog
from app.modules.notifications.service import create_notification
from app.modules.requirements.schemas import RequirementCreate, RequirementUpdate, RequirementResponse
from app.modules.resumes.service import get_allowed_client_ids


async def get_requirements(
    db: AsyncSession,
    current_user: User,
    client_id: uuid.UUID | None = None,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> list[RequirementResponse]:
    allowed_clients = await get_allowed_client_ids(db, current_user)

    query = (
        select(Requirement, Client.company_name)
        .join(Client, Requirement.client_id == Client.id)
    )

    if allowed_clients is not None:
        query = query.where(Requirement.client_id.in_(allowed_clients))

    if client_id:
        if allowed_clients is not None and client_id not in allowed_clients:
            return []
        query = query.where(Requirement.client_id == client_id)

    if status and status != "all":
        query = query.where(Requirement.status == status)
    elif not status:
        query = query.where(Requirement.status != "archived")

    if priority and priority != "all":
        query = query.where(Requirement.priority == priority)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Requirement.company.ilike(search_term),
                Requirement.role.ilike(search_term),
                Requirement.job_title.ilike(search_term),
                Requirement.role_code.ilike(search_term),
                Client.company_name.ilike(search_term),
            )
        )

    query = query.order_by(Requirement.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    response = []
    for req, client_name in rows:
        res_count = (
            await db.execute(
                select(func.count(Resume.id)).where(Resume.requirement_id == req.id)
            )
        ).scalar() or 0

        app_count = (
            await db.execute(
                select(func.count(Application.id)).where(Application.requirement_id == req.id)
            )
        ).scalar() or 0

        creator_name = req.creator.name if req.creator else None
        completer_name = req.completer.name if req.completer else None
        job_title = req.job_title or req.role

        response.append(
            RequirementResponse(
                id=req.id,
                client_id=req.client_id,
                client_name=client_name,
                company=req.company,
                job_title=job_title,
                role=req.role,
                role_code=req.role_code,
                job_url=req.job_url,
                priority=req.priority or "Medium",
                notes=req.notes,
                status=req.status,
                created_by=req.created_by,
                creator_name=creator_name,
                completed_by=req.completed_by,
                completer_name=completer_name,
                created_at=req.created_at,
                completed_at=req.completed_at,
                total_resumes=res_count,
                total_applications=app_count,
            )
        )

    return response


async def get_requirement_by_id(
    db: AsyncSession, req_id: uuid.UUID, current_user: User
) -> Requirement | None:
    allowed_clients = await get_allowed_client_ids(db, current_user)
    result = await db.execute(select(Requirement).where(Requirement.id == req_id))
    req = result.scalar_one_or_none()
    if not req:
        return None

    if allowed_clients is not None and req.client_id not in allowed_clients:
        raise HTTPException(status_code=403, detail="Forbidden: Not assigned to this client job opening")
    return req


async def create_requirement(
    db: AsyncSession, current_user: User, payload: RequirementCreate
) -> Requirement:
    # Role check: Employee cannot create jobs
    if current_user.role == "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot create Job Openings. Employees only complete assigned jobs.",
        )

    # Client can only create for their own company
    client_id = payload.client_id
    if current_user.role == "client":
        if not current_user.client_id:
            raise HTTPException(status_code=400, detail="Client user is not linked to a Service Client.")
        client_id = current_user.client_id

    if not client_id:
        raise HTTPException(status_code=400, detail="Service Client ID is required.")

    allowed_clients = await get_allowed_client_ids(db, current_user)
    if allowed_clients is not None and client_id not in allowed_clients:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot create job for unassigned client.")

    job_title = payload.job_title or payload.role or "Open Role"
    role = payload.role or job_title

    role_code = payload.role_code
    if not role_code:
        prefix = "".join(c for c in payload.company if c.isalnum())[:3].upper() or "JOB"
        role_part = "".join(c for c in job_title if c.isalnum())[:4].upper()
        role_code = f"{prefix}-{role_part}-{uuid.uuid4().hex[:4].upper()}"

    req = Requirement(
        client_id=client_id,
        company=payload.company.strip(),
        job_title=job_title.strip(),
        role=role.strip(),
        role_code=role_code.strip().upper(),
        job_url=payload.job_url.strip() if payload.job_url else None,
        priority=payload.priority or "Medium",
        notes=payload.notes.strip() if payload.notes else None,
        status=payload.status or "active",
        created_by=current_user.id,
    )
    db.add(req)
    await db.flush()

    actor_label = "Admin" if current_user.role == "admin" else ("Client" if current_user.role == "client" else "Sub-Admin")
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_created",
            details={
                "requirement_id": str(req.id),
                "role_code": req.role_code,
                "company": req.company,
                "job_title": req.job_title,
                "message": f"{actor_label} created {req.company} – {req.job_title}.",
            },
        )
    )
    await db.flush()
    return req


async def update_requirement(
    db: AsyncSession, current_user: User, req: Requirement, payload: RequirementUpdate
) -> Requirement:
    if current_user.role == "employee":
        raise HTTPException(status_code=403, detail="Employees cannot edit job openings.")

    if current_user.role == "client" and req.client_id != current_user.client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if payload.company is not None:
        req.company = payload.company.strip()
    if payload.job_title is not None:
        req.job_title = payload.job_title.strip()
        req.role = req.job_title
    elif payload.role is not None:
        req.role = payload.role.strip()
        req.job_title = req.role
    if payload.role_code is not None:
        req.role_code = payload.role_code.strip().upper()
    if payload.job_url is not None:
        req.job_url = payload.job_url.strip() if payload.job_url else None
    if payload.priority is not None:
        req.priority = payload.priority
    if payload.notes is not None:
        req.notes = payload.notes.strip() if payload.notes else None
    if payload.status is not None:
        req.status = payload.status

    actor_label = "Admin" if current_user.role == "admin" else ("Client" if current_user.role == "client" else "Sub-Admin")
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_updated",
            details={
                "requirement_id": str(req.id),
                "company": req.company,
                "job_title": req.job_title or req.role,
                "message": f"{actor_label} updated {req.company} – {req.job_title or req.role}.",
            },
        )
    )
    await db.flush()
    return req


async def mark_requirement_done(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")

    req.status = "done"
    req.completed_by = current_user.id
    req.completed_at = datetime.now(timezone.utc)
    await db.flush()

    job_name = f"{req.company} – {req.job_title or req.role}"

    # 1. Notify Admins
    admins = (await db.execute(select(User).where(User.role == "admin", User.is_active == True))).scalars().all()
    for adm in admins:
        await create_notification(
            db=db,
            user_id=adm.id,
            title="Job Opening Completed",
            message=f"{current_user.name} completed {job_name}.",
            notification_type="success",
        )

    # 2. Notify Client users
    client_users = (await db.execute(select(User).where(User.client_id == req.client_id, User.is_active == True))).scalars().all()
    for cu in client_users:
        await create_notification(
            db=db,
            user_id=cu.id,
            title="Job Opening Completed",
            message=f"Your {job_name} job has been completed.",
            notification_type="success",
        )

    # 3. Notify Employee
    if current_user.role == "employee":
        await create_notification(
            db=db,
            user_id=current_user.id,
            title="Job Completed",
            message=f"Job {job_name} marked as completed.",
            notification_type="success",
        )

    # 4. Activity Log
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_completed",
            details={
                "requirement_id": str(req.id),
                "company": req.company,
                "job_title": req.job_title or req.role,
                "message": f"{current_user.name} marked {job_name} as completed.",
            },
        )
    )
    await db.flush()
    return req


async def reopen_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")

    req.status = "active"
    req.completed_by = None
    req.completed_at = None
    await db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_reopened",
            details={"requirement_id": str(req.id), "company": req.company, "job_title": req.job_title or req.role},
        )
    )
    await db.flush()
    return req


async def archive_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")

    if current_user.role == "employee":
        raise HTTPException(status_code=403, detail="Employees cannot archive job openings.")

    req.status = "archived"
    await db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_archived",
            details={"requirement_id": str(req.id), "company": req.company, "job_title": req.job_title or req.role},
        )
    )
    await db.flush()
    return req


async def safe_delete_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> None:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")

    if current_user.role not in ["admin", "sub_admin"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check dependencies
    res_count = (await db.execute(select(func.count(Resume.id)).where(Resume.requirement_id == req_id))).scalar() or 0
    app_count = (await db.execute(select(func.count(Application.id)).where(Application.requirement_id == req_id))).scalar() or 0

    if res_count > 0 or app_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete job opening with linked resumes or applications. Archive instead.",
        )

    comp = req.company
    job_t = req.job_title or req.role
    await db.delete(req)

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_deleted",
            details={"requirement_id": str(req_id), "company": comp, "job_title": job_t},
        )
    )
    await db.flush()
