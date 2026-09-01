import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.reports import service
from app.modules.users.models import User
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/excel", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def export_excel_report(
    client_id: uuid.UUID | None = Query(None),
    employee_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download Excel spreadsheet report with multi-sheet application and resume metrics."""
    excel_bytes = await service.generate_excel_report(db, current_user=current_user, client_id=client_id, employee_id=employee_id)
    return FastAPIResponse(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="ApplyFlow_Recruitment_Report.xlsx"'
        },
    )


@router.get("/pdf", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def export_pdf_report(
    client_id: uuid.UUID | None = Query(None),
    employee_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download branded PDF recruitment summary report."""
    pdf_bytes = await service.generate_pdf_report(db, current_user=current_user, client_id=client_id, employee_id=employee_id)
    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="ApplyFlow_Recruitment_Report.pdf"'
        },
    )


@router.get("/export/clients", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def export_clients_csv(
    status: str = Query("active"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Active or Archived Clients as CSV."""
    csv_data = await service.export_clients_csv(db, current_user, status=status)
    return FastAPIResponse(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="ApplyFlow_{status}_clients.csv"'
        },
    )


@router.get("/export/employees", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def export_employees_csv(
    status: str = Query("inactive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Inactive / Active Employees as CSV."""
    csv_data = await service.export_employees_csv(db, current_user, status=status)
    return FastAPIResponse(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="ApplyFlow_{status}_employees.csv"'
        },
    )


@router.get("/export/targets", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def export_targets_csv(
    status: str = Query("ended"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Completed / Ended Targets as CSV."""
    csv_data = await service.export_targets_csv(db, current_user, status=status)
    return FastAPIResponse(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="ApplyFlow_{status}_targets.csv"'
        },
    )
