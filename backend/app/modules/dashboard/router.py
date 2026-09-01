import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.modules.dashboard import service
from app.modules.dashboard.schemas import (
    AdminClientCard,
    AdminHomeResponse,
    AdminOverviewMetrics,
    ClientDashboardResponse,
    ClientHomeResponse,
    EmployeeDashboardResponse,
    EmployeeHomeResponse,
    PerformanceStatsResponse,
    TargetSummary,
)
from app.modules.users.models import User
from app.modules.users.service import get_employee_performance_list
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _apply_deprecation_headers(response: Response, successor: str = "/api/dashboard/home") -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "v2"
    response.headers["Link"] = f'<{successor}>; rel="successor-version"'


@router.get("/home")
async def get_dashboard_home_universal(
    client_id: uuid.UUID | None = Query(None, description="Filter by Service Client ID"),
    employee_id: uuid.UUID | None = Query(None, description="Filter by Employee ID"),
    date_range: str | None = Query("today", description="Filter by date range"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Universal Single Dashboard Endpoint:
    Dispatches by role and returns all metrics, cards, targets, attendance, and metadata in 1 request.
    """
    effective_range = custom_date or date_filter or date_range or "today"
    if current_user.role in ("admin", "sub_admin"):
        return await service.get_admin_dashboard_home(
            db, current_user=current_user, client_id=client_id, employee_id=employee_id, date_range=effective_range, custom_date=custom_date
        )
    elif current_user.role == "employee":
        return await service.get_employee_dashboard_home(
            db, current_user=current_user, client_id=client_id, date_range=effective_range, custom_date=custom_date
        )
    elif current_user.role == "client":
        return await service.get_client_dashboard_home(db, current_user=current_user)
    else:
        return await service.get_admin_dashboard_home(
            db, current_user=current_user, client_id=client_id, employee_id=employee_id, date_range=effective_range, custom_date=custom_date
        )


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


@router.get("/admin/overview", response_model=AdminOverviewMetrics, deprecated=True, dependencies=[Depends(require_role("admin", "sub_admin"))])
@router.get("/overview", response_model=AdminOverviewMetrics, deprecated=True, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_overview(
    response: Response,
    client_id: uuid.UUID | None = Query(None, description="Filter by Service Client ID"),
    employee_id: uuid.UUID | None = Query(None, description="Filter by Employee ID"),
    date_range: str | None = Query(None, description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/admin/home] Admin/Sub-Admin Overview with cascading filtering."""
    _apply_deprecation_headers(response, "/api/dashboard/admin/home")
    effective_range = custom_date or date_filter or date_range
    return await service.get_admin_overview(
        db, current_user=current_user, client_id=client_id, employee_id=employee_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/admin/employees", deprecated=True, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_employees_view(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/admin/home] Admin/Sub-Admin Employee performance table."""
    _apply_deprecation_headers(response, "/api/dashboard/admin/home")
    return await get_employee_performance_list(db, current_user=current_user)


@router.get("/admin/clients", response_model=list[AdminClientCard], deprecated=True, dependencies=[Depends(require_role("admin", "sub_admin"))])
async def get_admin_clients_view(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/admin/home] Admin/Sub-Admin Client performance cards."""
    _apply_deprecation_headers(response, "/api/dashboard/admin/home")
    return await service.get_admin_clients_summary(db, current_user=current_user)


@router.get("/employee/target-summary", response_model=TargetSummary, deprecated=True)
async def get_employee_target_summary_endpoint(
    response: Response,
    client_id: uuid.UUID | None = Query(None, description="Filter by assigned Service Client ID"),
    date_range: str | None = Query("today", description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/employee/home] Daily Target Quota single source of truth."""
    _apply_deprecation_headers(response, "/api/dashboard/employee/home")
    from app.modules.clients.models import EmployeeClient
    from app.modules.dashboard.service import _parse_date_filter

    assigned_q = select(EmployeeClient.client_id).where(
        EmployeeClient.employee_id == current_user.id,
        EmployeeClient.active == True,
    )
    assigned_cids = (await db.execute(assigned_q)).scalars().all()

    target_clients = [client_id] if (client_id and client_id in assigned_cids) else assigned_cids
    effective_range = custom_date or date_filter or date_range or "today"
    start_dt, next_dt, filter_d, num_days = _parse_date_filter(effective_range, custom_date)

    return await service.get_employee_target_summary(
        db=db,
        employee_id=current_user.id,
        client_ids=target_clients,
        start_dt=start_dt,
        next_dt=next_dt,
        filter_d=filter_d,
        num_days=num_days,
    )


@router.get("/employee", response_model=EmployeeDashboardResponse, deprecated=True)
async def get_employee_dashboard(
    response: Response,
    client_id: uuid.UUID | None = Query(None, description="Filter by assigned Service Client ID"),
    date_range: str | None = Query(None, description="Filter by date range (today, yesterday, this_week, this_month)"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/employee/home] Employee Dashboard isolated metrics."""
    _apply_deprecation_headers(response, "/api/dashboard/employee/home")
    effective_range = custom_date or date_filter or date_range
    return await service.get_employee_dashboard(
        db, current_user, client_id=client_id, date_range=effective_range, custom_date=custom_date
    )


@router.get("/client", response_model=ClientDashboardResponse, deprecated=True)
async def get_client_dashboard(
    response: Response,
    date_range: str | None = Query(None, description="Filter by date range"),
    date_filter: str | None = Query(None, description="Alias for date range"),
    custom_date: str | None = Query(None, description="Custom date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEPRECATED: Use /api/dashboard/client/home] Client Dashboard."""
    _apply_deprecation_headers(response, "/api/dashboard/client/home")
    effective_range = custom_date or date_filter or date_range
    return await service.get_client_dashboard(db, current_user, date_range=effective_range, custom_date=custom_date)
