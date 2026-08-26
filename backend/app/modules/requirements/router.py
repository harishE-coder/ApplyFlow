import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.users.models import User
from app.modules.requirements.schemas import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
)
from app.modules.requirements import service

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    client_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List job requirements:
    - Admin: sees all requirements
    - Employee: sees requirements for assigned clients
    - Client: sees their own company requirements
    """
    return await service.get_requirements(
        db=db,
        current_user=current_user,
        client_id=client_id,
        status=status,
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
        raise HTTPException(status_code=404, detail="Requirement not found")
    all_reqs = await service.get_requirements(db, current_user, search=req.role_code)
    for r in all_reqs:
        if r.id == req_id:
            return r
    raise HTTPException(status_code=404, detail="Requirement not found")


@router.post("", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new requirement (Admin or Client)."""
    if current_user.role not in ["admin", "sub_admin", "client"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    req = await service.create_requirement(db, current_user, payload)
    all_reqs = await service.get_requirements(db, current_user, client_id=payload.client_id)
    for r in all_reqs:
        if r.id == req.id:
            return r
    return RequirementResponse.model_validate(req)


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
        raise HTTPException(status_code=404, detail="Requirement not found")

    await service.update_requirement(db, current_user, req, payload)
    all_reqs = await service.get_requirements(db, current_user, client_id=req.client_id)
    for r in all_reqs:
        if r.id == req_id:
            return r
    return RequirementResponse.model_validate(req)


@router.post("/{req_id}/close")
async def close_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Close job opening (stays searchable)."""
    await service.close_requirement(db, req_id, current_user)
    return {"message": "Requirement closed successfully"}


@router.post("/{req_id}/reopen")
async def reopen_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reopen a closed job opening."""
    await service.reopen_requirement(db, req_id, current_user)
    return {"message": "Requirement reopened successfully"}


@router.post("/{req_id}/archive")
async def archive_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive job opening."""
    await service.archive_requirement(db, req_id, current_user)
    return {"message": "Requirement archived successfully"}


@router.delete("/{req_id}")
async def delete_requirement_endpoint(
    req_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Safe delete requirement (allowed only if no delivered resumes/applications)."""
    await service.safe_delete_requirement(db, req_id, current_user)
    return {"message": "Requirement deleted successfully"}
