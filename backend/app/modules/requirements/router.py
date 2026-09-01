import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.requirements import service
from app.modules.requirements.schemas import (
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    client_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List job openings:
    - Admin: sees all job openings
    - Sub-Admin: sees job openings for assigned clients
    - Employee: sees job openings for assigned clients
    - Client: sees their own company job openings
    """
    return await service.get_requirements(
        db=db,
        current_user=current_user,
        client_id=client_id,
        status=status,
        priority=priority,
        search=search,
    )


@router.get("/{req_id}", response_model=RequirementResponse)
async def get_requirement(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await service.get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")
    all_reqs = await service.get_requirements(db, current_user, search=req.company)
    for r in all_reqs:
        if r.id == req_id:
            return r
    raise HTTPException(status_code=404, detail="Job opening not found")


@router.post("", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new job opening task (Admin, Sub-Admin, or Client). Employee is blocked."""
    req = await service.create_requirement(db, current_user, payload)
    all_reqs = await service.get_requirements(db, current_user, client_id=req.client_id, status="all")
    for r in all_reqs:
        if r.id == req.id:
            return r
    return RequirementResponse(
        id=req.id,
        client_id=req.client_id,
        client_name=req.client.company_name if req.client else "",
        company=req.company,
        job_title=req.job_title or req.role,
        role=req.role,
        role_code=req.role_code,
        job_url=req.job_url,
        priority=req.priority or "Medium",
        notes=req.notes,
        status=req.status,
        created_by=req.created_by,
        creator_name=current_user.name,
        created_at=req.created_at,
    )


@router.put("/{req_id}", response_model=RequirementResponse)
@router.patch("/{req_id}", response_model=RequirementResponse)
async def update_requirement(
    req_id: uuid.UUID,
    payload: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await service.get_requirement_by_id(db, req_id, current_user)
    if not req:
        raise HTTPException(status_code=404, detail="Job opening not found")

    await service.update_requirement(db, current_user, req, payload)
    all_reqs = await service.get_requirements(db, current_user, client_id=req.client_id, status="all")
    for r in all_reqs:
        if r.id == req_id:
            return r
    raise HTTPException(status_code=404, detail="Job opening not found")


@router.post("/{req_id}/done", response_model=RequirementResponse, dependencies=[Depends(require_role("employee"))])
@router.post("/{req_id}/complete", response_model=RequirementResponse, dependencies=[Depends(require_role("employee"))])
async def mark_requirement_done_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark job opening as completed (Done). Moves to completed history, creates notifications & audit log."""
    req = await service.mark_requirement_done(db, req_id, current_user)
    all_reqs = await service.get_requirements(db, current_user, client_id=req.client_id, status="done")
    for r in all_reqs:
        if r.id == req_id:
            return r
    raise HTTPException(status_code=404, detail="Job opening not found")


@router.post("/{req_id}/reopen")
async def reopen_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reopen a completed/closed job opening."""
    await service.reopen_requirement(db, req_id, current_user)
    return {"message": "Job opening reopened successfully"}


@router.post("/{req_id}/archive")
async def archive_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive job opening."""
    await service.archive_requirement(db, req_id, current_user)
    return {"message": "Job opening archived successfully"}


@router.post("/{req_id}/close")
async def close_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Close job opening (alias to complete/done)."""
    await service.mark_requirement_done(db, req_id, current_user)
    return {"message": "Job opening marked as done"}


@router.delete("/{req_id}")
async def delete_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Safe delete job opening (allowed only if no linked resumes/applications)."""
    await service.safe_delete_requirement(db, req_id, current_user)
    return {"message": "Job opening deleted successfully"}
