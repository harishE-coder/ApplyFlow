import uuid
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.activity_logs.models import ActivityLog
from app.modules.requirements.schemas import RequirementCreate, RequirementUpdate, RequirementResponse
from app.modules.resumes.service import get_allowed_client_ids


async def get_requirements(
    db: AsyncSession,
    current_user: User,
    client_id: uuid.UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[RequirementResponse]:
    allowed_clients = await get_allowed_client_ids(db, current_user)

    query = select(Requirement, Client.company_name).join(Client, Requirement.client_id == Client.id)

    if allowed_clients is not None:
        query = query.where(Requirement.client_id.in_(allowed_clients))

    if client_id:
        if allowed_clients is not None and client_id not in allowed_clients:
            return []
        query = query.where(Requirement.client_id == client_id)

    if status and status != "all":
        query = query.where(Requirement.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Requirement.company.ilike(search_term),
                Requirement.role.ilike(search_term),
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

        response.append(
            RequirementResponse(
                id=req.id,
                client_id=req.client_id,
                client_name=client_name,
                company=req.company,
                role=req.role,
                role_code=req.role_code,
                status=req.status,
                created_at=req.created_at,
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
        raise HTTPException(status_code=403, detail="Forbidden: Not assigned to this client requirement")
    return req


async def create_requirement(
    db: AsyncSession, current_user: User, payload: RequirementCreate
) -> Requirement:
    allowed_clients = await get_allowed_client_ids(db, current_user)
    if allowed_clients is not None and payload.client_id not in allowed_clients:
        raise HTTPException(status_code=403, detail="Forbidden")

    req = Requirement(
        client_id=payload.client_id,
        company=payload.company.strip(),
        role=payload.role.strip(),
        role_code=payload.role_code.strip().upper(),
        status=payload.status or "active",
    )
    db.add(req)
    await db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_created",
            details={"requirement_id": str(req.id), "role_code": req.role_code},
        )
    )
    return req


async def update_requirement(
    db: AsyncSession, current_user: User, req: Requirement, payload: RequirementUpdate
) -> Requirement:
    if payload.company is not None:
        req.company = payload.company.strip()
    if payload.role is not None:
        req.role = payload.role.strip()
    if payload.role_code is not None:
        req.role_code = payload.role_code.strip().upper()
    if payload.status is not None:
        req.status = payload.status
    await db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_updated",
            details={"requirement_id": str(req.id), "role_code": req.role_code},
        )
    )
    return req


async def close_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    req.status = "closed"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_closed",
            details={"requirement_id": str(req.id), "role_code": req.role_code},
        )
    )
    await db.flush()
    return req


async def reopen_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    req.status = "active"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_reopened",
            details={"requirement_id": str(req.id), "role_code": req.role_code},
        )
    )
    await db.flush()
    return req


async def archive_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> Requirement:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    req.status = "archived"
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_archived",
            details={"requirement_id": str(req.id), "role_code": req.role_code},
        )
    )
    await db.flush()
    return req


async def safe_delete_requirement(db: AsyncSession, req_id: uuid.UUID, current_user: User) -> None:
    req = await get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    res_count = (await db.execute(select(func.count(Resume.id)).where(Resume.requirement_id == req_id))).scalar() or 0
    app_count = (await db.execute(select(func.count(Application.id)).where(Application.requirement_id == req_id))).scalar() or 0

    if res_count > 0 or app_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This requirement has delivered resumes/applications. Close or archive instead.",
        )

    await db.delete(req)
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="requirement_deleted",
            details={"requirement_id": str(req_id), "role_code": req.role_code},
        )
    )
    await db.flush()
