import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.users.models import User
from app.modules.dashboard.schemas import (
    AdminOverviewMetrics,
    AdminClientCard,
    EmployeeDashboardResponse,
    ClientDashboardResponse,
    TargetSummary,
    AdminHomeResponse,
    EmployeeHomeResponse,
    ClientHomeResponse,
    PerformanceStatsResponse,
)
from app.modules.dashboard import service
from app.modules.users.service import get_employee_performance_list
from sqlalchemy import select

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/admin/home", response_model=AdminHomeResponse, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_dashboard_home_endpoint(
    client_id: uuid.UUID | None = Query(None, description="Filter by Service Client ID"),
    employee_id: uuid.UUID | None = Query(None, description="Filter by Employee ID"),
    date_range: str | None = Query("today", description="Filter by date range"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated Super Admin & Sub-Admin Dashboard Home: returns all metrics, cards, charts, and metadata in 1 roundtrip."""
    effective_range = custom_date or date_filter or date_range or "today"
    return await service.get_admin_dashboard_home(
        db, current_user=current_user, client_id=client_id, employee_id=employee_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/employee/home", response_model=EmployeeHomeResponse)
async def get_employee_dashboard_home_endpoint(
    client_id: uuid.UUID | None = Query(None, description="Filter by assigned Service Client ID"),
    date_range: str | None = Query("today", description="Filter by date range"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated Recruiter / Employee Dashboard Home in 1 roundtrip."""
    effective_range = custom_date or date_filter or date_range or "today"
    return await service.get_employee_dashboard_home(
        db, current_user=current_user, client_id=client_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/client/home", response_model=ClientHomeResponse)
async def get_client_dashboard_home_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consolidated Client Portal Dashboard Home in 1 roundtrip."""
    return await service.get_client_dashboard_home(db, current_user=current_user)


@router.get("/performance", response_model=PerformanceStatsResponse)
async def get_performance_stats_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real-time architecture and database telemetry diagnostics."""
    return await service.get_dashboard_performance_metrics(db)


@router.get("/admin/overview", response_model=AdminOverviewMetrics, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.get("/overview", response_model=AdminOverviewMetrics, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_overview(
    client_id: uuid.UUID | None = Query(None, description="Filter by Service Client ID"),
    employee_id: uuid.UUID | None = Query(None, description="Filter by Employee ID"),
    date_range: str | None = Query(None, description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/Sub-Admin Overview with cascading filtering: Service Client + Employee + Global Date Filter."""
    effective_range = custom_date or date_filter or date_range
    return await service.get_admin_overview(
        db, current_user=current_user, client_id=client_id, employee_id=employee_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/admin/employees", dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_employees_view(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/Sub-Admin Employee View: performance table with targets and completion %."""
    return await get_employee_performance_list(db, current_user=current_user)


@router.get("/admin/clients", response_model=list[AdminClientCard], dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_clients_view(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin/Sub-Admin Client View: client cards, active recruiters, daily trends."""
    return await service.get_admin_clients_summary(db, current_user=current_user)


@router.get("/employee/target-summary", response_model=TargetSummary)
async def get_employee_target_summary_endpoint(
    client_id: uuid.UUID | None = Query(None, description="Filter by assigned Service Client ID"),
    date_range: str | None = Query("today", description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Real-time live calculation of Daily Target Quota single source of truth."""
    from app.modules.dashboard.service import _parse_date_filter
    from app.modules.clients.models import EmployeeClient

    assigned_q = select(EmployeeClient.client_id).where(
        EmployeeClient.employee_id == current_user.id,
        EmployeeClient.active == True,
    )
    assigned_cids = (await db.execute(assigned_q)).scalars().all()

    target_clients = [client_id] if (client_id and client_id in assigned_cids) else assigned_cids
    effective_range = custom_date or date_filter or date_range or "today"
    start_dt, end_dt, filter_d = _parse_date_filter(effective_range, custom_date)

    return await service.get_employee_target_summary(
        db=db,
        employee_id=current_user.id,
        client_ids=target_clients,
        start_dt=start_dt,
        end_dt=end_dt,
        filter_d=filter_d,
    )


@router.get("/employee", response_model=EmployeeDashboardResponse)
async def get_employee_dashboard(
    client_id: uuid.UUID | None = Query(None, description="Filter by assigned Service Client ID"),
    date_range: str | None = Query(None, description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Employee Dashboard: isolated metrics by assigned Service Client + Global Date Filter."""
    effective_range = custom_date or date_filter or date_range
    return await service.get_employee_dashboard(
        db, current_user, client_id=client_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/client", response_model=ClientDashboardResponse)
async def get_client_dashboard(
    date_range: str | None = Query(None, description="Filter by date range"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Client Dashboard: applications received, available resumes, roles breakdown with Global Date Filter."""
    effective_range = custom_date or date_filter or date_range
    return await service.get_client_dashboard(db, current_user, date_range=effective_range, custom_date=custom_date)
