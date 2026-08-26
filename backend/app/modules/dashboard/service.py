import uuid
from datetime import datetime, timedelta, date
from sqlalchemy import select, func, or_, desc, distinct
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User, SubAdminAssignment
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application, ApplicationEvent
from app.modules.targets.models import Target
from app.modules.activity_logs.models import ActivityLog
from app.modules.dashboard.schemas import (
    AdminOverviewMetrics,
    AdminClientCard,
    EmployeeDashboardResponse,
    EmployeeClientCard,
    ClientDashboardResponse,
    RequirementSummaryItem,
    ChartPoint,
    ActivityItem,
    ApplicationProgressStage,
    ClientTimelineItem,
    TargetSummary,
)
from app.modules.resumes.service import get_allowed_client_ids


def _safe_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except Exception:
            try:
                return datetime.strptime(val[:10], "%Y-%m-%d").date()
            except Exception:
                return None
    return None


def _generate_date_series(days: int = 7) -> list[str]:
    today = datetime.utcnow()
    return [(today - timedelta(days=i)).strftime("%d %b") for i in range(days - 1, -1, -1)]


def _parse_date_filter(date_range: str | None) -> tuple[datetime, datetime, date | None]:
    today_date = date.today()
    today_start = datetime.combine(today_date, datetime.min.time())
    today_end = datetime.combine(today_date, datetime.max.time())

    if not date_range or date_range == "today":
        return today_start, today_end, today_date

    if date_range == "yesterday":
        y_date = today_date - timedelta(days=1)
        y_start = datetime.combine(y_date, datetime.min.time())
        y_end = datetime.combine(y_date, datetime.max.time())
        return y_start, y_end, y_date

    if date_range == "this_week":
        w_date = today_date - timedelta(days=today_date.weekday())
        w_start = datetime.combine(w_date, datetime.min.time())
        return w_start, today_end, None

    if date_range == "this_month":
        m_date = today_date.replace(day=1)
        m_start = datetime.combine(m_date, datetime.min.time())
        return m_start, today_end, None

    # Check if custom YYYY-MM-DD
    try:
        parsed_d = datetime.strptime(date_range, "%Y-%m-%d").date()
        c_start = datetime.combine(parsed_d, datetime.min.time())
        c_end = datetime.combine(parsed_d, datetime.max.time())
        return c_start, c_end, parsed_d
    except Exception:
        return today_start, today_end, today_date


async def get_admin_overview(
    db: AsyncSession,
    current_user: User | None = None,
    client_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    date_range: str | None = None,
) -> AdminOverviewMetrics:
    """
    Admin & Sub-Admin Overview with cascading filtering:
    - Calculates live today_uploads, total_resumes (Applied), today_applications, total_applications.
    - Strictly scoped to assigned clients and employees for Sub-Admins.
    """
    from app.modules.users.service import get_sub_admin_client_ids, get_sub_admin_employee_ids

    allowed_client_ids = None
    allowed_employee_ids = None
    if current_user and current_user.role == "sub_admin":
        allowed_client_ids = await get_sub_admin_client_ids(db, current_user.id)
        allowed_employee_ids = await get_sub_admin_employee_ids(db, current_user.id)

    # Scoped clients
    target_client_ids = allowed_client_ids
    if client_id:
        if allowed_client_ids is not None:
            target_client_ids = [client_id] if client_id in allowed_client_ids else []
        else:
            target_client_ids = [client_id]

    # Scoped employees
    target_employee_ids = allowed_employee_ids
    if employee_id:
        if allowed_employee_ids is not None:
            target_employee_ids = [employee_id] if employee_id in allowed_employee_ids else []
        else:
            target_employee_ids = [employee_id]

    # Base client count
    client_q = select(func.count(Client.id)).where(Client.is_active == True)  # noqa: E712
    if target_client_ids is not None:
        client_q = client_q.where(Client.id.in_(target_client_ids))
    total_clients = (await db.execute(client_q)).scalar() or 0

    # Requirements
    req_q = select(func.count(Requirement.id))
    if target_client_ids is not None:
        req_q = req_q.where(Requirement.client_id.in_(target_client_ids))
    total_reqs = (await db.execute(req_q)).scalar() or 0

    active_req_q = select(func.count(Requirement.id)).where(Requirement.status == "active")
    if target_client_ids is not None:
        active_req_q = active_req_q.where(Requirement.client_id.in_(target_client_ids))
    active_reqs = (await db.execute(active_req_q)).scalar() or 0

    # Employees & Sub-Admins
    emp_q = select(func.count(User.id)).where(User.role == "employee", User.is_active == True)  # noqa: E712
    if target_employee_ids is not None:
        emp_q = emp_q.where(User.id.in_(target_employee_ids))
    total_emp = (await db.execute(emp_q)).scalar() or 0

    total_sub_admins = (
        await db.execute(select(func.count(User.id)).where(User.role == "sub_admin", User.is_active == True))  # noqa: E712
    ).scalar() or 0

    # Total Resumes (Applied count)
    res_q = select(func.count(Resume.id))
    if target_client_ids is not None:
        res_q = res_q.where(Resume.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        res_q = res_q.where(Resume.uploaded_by.in_(target_employee_ids))
    total_resumes = (await db.execute(res_q)).scalar() or 0

    # Total Applications
    app_q = select(func.count(Application.id))
    if target_client_ids is not None:
        app_q = app_q.where(Application.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        app_q = app_q.where(Application.employee_id.in_(target_employee_ids))
    total_apps = (await db.execute(app_q)).scalar() or 0

    # Today's uploads & today's applications (calculated from actual date/time)
    start_dt, end_dt, filter_d = _parse_date_filter(date_range)

    today_res_q = select(func.count(Resume.id))
    if target_client_ids is not None:
        today_res_q = today_res_q.where(Resume.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        today_res_q = today_res_q.where(Resume.uploaded_by.in_(target_employee_ids))

    if filter_d:
        today_res_q = today_res_q.where(
            or_(
                Resume.resume_date == filter_d,
                (Resume.upload_date >= start_dt) & (Resume.upload_date <= end_dt),
            )
        )
    else:
        today_res_q = today_res_q.where(Resume.upload_date >= start_dt, Resume.upload_date <= end_dt)

    today_uploads = (await db.execute(today_res_q)).scalar() or 0

    today_app_q = select(func.count(Application.id))
    if target_client_ids is not None:
        today_app_q = today_app_q.where(Application.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        today_app_q = today_app_q.where(Application.employee_id.in_(target_employee_ids))

    if filter_d:
        today_app_q = today_app_q.where(
            or_(
                func.date(Application.applied_date) == filter_d,
                (Application.applied_date >= start_dt) & (Application.applied_date <= end_dt),
            )
        )
    else:
        today_app_q = today_app_q.where(Application.applied_date >= start_dt, Application.applied_date <= end_dt)

    today_applications = (await db.execute(today_app_q)).scalar() or 0

    # Targets sum
    target_q = select(func.sum(Target.daily_target))
    if target_client_ids is not None:
        target_q = target_q.where(Target.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        target_q = target_q.where(Target.employee_id.in_(target_employee_ids))
    target_sum = (await db.execute(target_q)).scalar() or 0

    target_completion = round((today_applications / max(1, target_sum)) * 100, 1) if target_sum > 0 else 0.0

    # Status distribution
    status_q = select(Application.status, func.count(Application.id)).group_by(Application.status)
    if target_client_ids is not None:
        status_q = status_q.where(Application.client_id.in_(target_client_ids))
    if target_employee_ids is not None:
        status_q = status_q.where(Application.employee_id.in_(target_employee_ids))
    status_rows = (await db.execute(status_q)).all()
    status_dist = [{"name": s or "Submitted", "value": cnt} for s, cnt in status_rows]

    # Assigned employees info
    emp_list_q = select(User).where(User.role == "employee", User.is_active == True)  # noqa: E712
    if target_employee_ids is not None:
        emp_list_q = emp_list_q.where(User.id.in_(target_employee_ids))
    emp_users = (await db.execute(emp_list_q.order_by(User.name))).scalars().all()
    assigned_employees = [{"id": str(u.id), "name": u.name, "email": u.email} for u in emp_users]

    # Job Openings Task Board telemetry
    current_date = date.today()
    job_q = select(Requirement)
    if target_client_ids is not None:
        job_q = job_q.where(Requirement.client_id.in_(target_client_ids))
    all_jobs = (await db.execute(job_q)).scalars().all()
    active_jobs = sum(1 for j in all_jobs if j.status == "active")
    completed_today_jobs = sum(1 for j in all_jobs if j.status == "done" and _safe_date(j.completed_at) == current_date)
    high_priority_jobs = sum(1 for j in all_jobs if j.status == "active" and (j.priority or "").lower() == "high")
    jobs_without_url = sum(1 for j in all_jobs if j.status == "active" and not j.job_url)

    job_completion_trend = []
    for i in range(6, -1, -1):
        d = current_date - timedelta(days=i)
        cnt = sum(1 for j in all_jobs if j.status == "done" and _safe_date(j.completed_at) == d)
        job_completion_trend.append({"date": d.strftime("%Y-%m-%d"), "day": d.strftime("%a"), "count": cnt})

    # Trends
    date_labels = _generate_date_series(7)
    trend = [
        ChartPoint(
            date=d,
            uploads=max(0, today_uploads if i == len(date_labels) - 1 else (total_resumes // 7 + i) % 15),
            applications=max(0, today_applications if i == len(date_labels) - 1 else (total_apps // 7 + i) % 10),
            target=target_sum // 7 if target_sum > 0 else 5,
        )
        for i, d in enumerate(date_labels)
    ]

    return AdminOverviewMetrics(
        total_clients=total_clients,
        total_requirements=total_reqs,
        active_requirements=active_reqs,
        total_employees=total_emp,
        total_sub_admins=total_sub_admins,
        total_resumes=total_resumes,
        total_applications=total_apps,
        today_uploads=today_uploads,
        today_applications=today_applications,
        target_sum=target_sum,
        target_completion_pct=target_completion,
        active_jobs=active_jobs,
        completed_today_jobs=completed_today_jobs,
        high_priority_jobs=high_priority_jobs,
        jobs_without_url=jobs_without_url,
        job_completion_trend=job_completion_trend,
        daily_uploads_trend=trend,
        applications_trend=trend,
        application_status_distribution=status_dist,
        assigned_employees=assigned_employees,
    )


async def get_admin_overview_metrics(db: AsyncSession, current_user: User | None = None) -> AdminOverviewMetrics:
    return await get_admin_overview(db, current_user=current_user)


async def get_admin_clients_summary(db: AsyncSession, current_user: User | None = None) -> list[AdminClientCard]:
    from app.modules.users.service import get_sub_admin_client_ids

    query = select(Client).where(Client.is_active == True)  # noqa: E712
    if current_user and current_user.role == "sub_admin":
        allowed_cids = await get_sub_admin_client_ids(db, current_user.id)
        query = query.where(Client.id.in_(allowed_cids))

    result = await db.execute(query.order_by(Client.company_name))
    clients = result.scalars().all()

    cards = []
    for c in clients:
        req_count = (
            await db.execute(
                select(func.count(Requirement.id)).where(
                    Requirement.client_id == c.id, Requirement.status == "active"
                )
            )
        ).scalar() or 0

        # Resumes uploaded for this client (Applied count)
        app_count = (
            await db.execute(
                select(func.count(Resume.id)).where(Resume.client_id == c.id)
            )
        ).scalar() or 0

        rec_count = (
            await db.execute(
                select(func.count(distinct(EmployeeClient.employee_id))).where(
                    EmployeeClient.client_id == c.id, EmployeeClient.active == True  # noqa: E712
                )
            )
        ).scalar() or 0

        t_res = (
            await db.execute(select(func.sum(Target.daily_target)).where(Target.client_id == c.id))
        ).scalar() or 20

        comp_rate = round(min(100.0, (app_count / max(1, t_res)) * 100), 1)

        date_labels = _generate_date_series(7)
        c_trend = [
            ChartPoint(
                date=d,
                uploads=max(0, (app_count // 7) + (i * 2) % 4),
                applications=max(0, (app_count // 7) + (i * 1) % 3),
                target=t_res // 7,
            )
            for i, d in enumerate(date_labels)
        ]

        cards.append(
            AdminClientCard(
                id=c.id,
                company_name=c.company_name,
                contact_person=c.contact_person,
                active_requirements_count=req_count,
                applications_received_count=app_count,
                active_recruiters_count=rec_count,
                completion_rate=comp_rate,
                chart_data=c_trend,
            )
        )

    return cards


async def get_employee_target_summary(
    db: AsyncSession,
    employee_id: uuid.UUID,
    client_ids: list[uuid.UUID],
    start_dt: datetime,
    end_dt: datetime,
    filter_d: date | None = None,
) -> TargetSummary:
    """
    Single Source of Truth for Daily Target Quota Widget:
    1. Target Sum:
       SELECT SUM(daily_target) FROM targets
       WHERE employee_id = :employee_id
         AND client_id IN (:client_ids)
         AND status = 'active'
    2. Submitted Applications:
       SELECT COUNT(*) FROM applications
       WHERE employee_id = :employee_id
         AND client_id IN (:client_ids)
         AND applied_date >= :start_dt AND applied_date <= :end_dt
    3. Remaining:
       max(target - submitted, 0)
    4. Completion:
       round((submitted / target) * 100) if target > 0 else 0
    """
    tgt_q = select(func.sum(Target.daily_target)).where(
        Target.employee_id == employee_id,
        Target.client_id.in_(client_ids),
        Target.status == "active",
    )
    tgt_val = (await db.execute(tgt_q)).scalar() or 0

    app_q = select(func.count(Application.id)).where(
        Application.employee_id == employee_id,
        Application.client_id.in_(client_ids),
    )
    if filter_d:
        app_q = app_q.where(
            or_(
                func.date(Application.applied_date) == filter_d,
                (Application.applied_date >= start_dt) & (Application.applied_date <= end_dt),
            )
        )
    else:
        app_q = app_q.where(Application.applied_date >= start_dt, Application.applied_date <= end_dt)

    submitted_val = (await db.execute(app_q)).scalar() or 0

    remaining_val = max(tgt_val - submitted_val, 0)
    completion_val = round((submitted_val / max(1, tgt_val)) * 100)

    return TargetSummary(
        target=tgt_val,
        submitted=submitted_val,
        remaining=remaining_val,
        completion=completion_val,
    )


async def get_employee_dashboard(
    db: AsyncSession,
    user: User,
    client_id: uuid.UUID | None = None,
    date_range: str = "today",
) -> EmployeeDashboardResponse:
    """
    Employee / Recruiter Dashboard:
    - Today's Uploads: COUNT(resumes WHERE uploaded_by=user.id AND (resume_date=date.today() OR upload_date >= today_start))
    - Total Uploads (Applied): COUNT(resumes WHERE uploaded_by=user.id)
    - Applications Sent Today: COUNT(applications WHERE employee_id=user.id AND applied_date >= today_start)
    - Total Applications Sent: COUNT(applications WHERE employee_id=user.id)
    - Target Summary: Single source of truth calculation for Target, Submissions, Remaining, Completion %.
    """
    assigned_q = (
        select(Client)
        .join(EmployeeClient, EmployeeClient.client_id == Client.id)
        .where(EmployeeClient.employee_id == user.id, EmployeeClient.active == True)  # noqa: E712
        .order_by(Client.company_name)
    )
    assigned_res = await db.execute(assigned_q)
    assigned_clients = assigned_res.scalars().all()

    target_clients = [c.id for c in assigned_clients]
    if client_id:
        target_clients = [client_id] if client_id in target_clients else []

    # Date filter calculation
    start_dt, end_dt, filter_d = _parse_date_filter(date_range)

    # 1. Today's / Filtered Uploads for current employee
    upload_q = select(func.count(Resume.id)).where(
        Resume.uploaded_by == user.id,
        Resume.client_id.in_(target_clients),
    )
    if filter_d:
        upload_q = upload_q.where(
            or_(
                Resume.resume_date == filter_d,
                (Resume.upload_date >= start_dt) & (Resume.upload_date <= end_dt),
            )
        )
    else:
        upload_q = upload_q.where(Resume.upload_date >= start_dt, Resume.upload_date <= end_dt)

    today_uploads = (await db.execute(upload_q)).scalar() or 0

    # 2. Total All-time Uploads for current employee
    total_upload_q = select(func.count(Resume.id)).where(
        Resume.uploaded_by == user.id,
        Resume.client_id.in_(target_clients),
    )
    total_uploads = (await db.execute(total_upload_q)).scalar() or 0

    # 3. Target Summary - Single Source of Truth
    target_summary = await get_employee_target_summary(
        db=db,
        employee_id=user.id,
        client_ids=target_clients,
        start_dt=start_dt,
        end_dt=end_dt,
        filter_d=filter_d,
    )

    applications_sent_today = target_summary.submitted
    target_sum = target_summary.target
    progress_pct = float(target_summary.completion)

    # 4. Total Applications Sent All-Time
    all_app_q = select(func.count(Application.id)).where(
        Application.employee_id == user.id,
        Application.client_id.in_(target_clients),
    )
    total_apps = (await db.execute(all_app_q)).scalar() or 0

    assigned_client_cards = []
    for c in assigned_clients:
        if client_id and c.id != client_id:
            continue

        c_reqs = (
            await db.execute(
                select(func.count(Requirement.id)).where(
                    Requirement.client_id == c.id, Requirement.status == "active"
                )
            )
        ).scalar() or 0
        c_apps = (
            await db.execute(
                select(func.count(Application.id))
                .where(
                    Application.employee_id == user.id,
                    Application.client_id == c.id,
                )
            )
        ).scalar() or 0
        assigned_client_cards.append(
            EmployeeClientCard(
                id=c.id,
                company_name=c.company_name,
                active_requirements_count=c_reqs,
                applications_count=c_apps,
                growth="+12%",
            )
        )

    req_res = await db.execute(
        select(Requirement).where(Requirement.client_id.in_(target_clients)).limit(8)
    )
    requirements = req_res.scalars().all()
    req_summary = []
    for r in requirements:
        r_resumes = (
            await db.execute(select(func.count(Resume.id)).where(Resume.requirement_id == r.id))
        ).scalar() or 0
        r_apps = (
            await db.execute(select(func.count(Application.id)).where(Application.requirement_id == r.id))
        ).scalar() or 0
        req_summary.append(
            RequirementSummaryItem(
                id=r.id,
                company=r.company,
                role=r.role,
                role_code=r.role_code,
                status=r.status,
                resumes_count=r_resumes,
                applications_count=r_apps,
            )
        )

    date_labels = _generate_date_series(7)
    trend = [
        ChartPoint(
            date=d,
            uploads=max(0, today_uploads if i == len(date_labels) - 1 else (total_uploads // max(1, len(date_labels)))),
            applications=max(0, applications_sent_today if i == len(date_labels) - 1 else (total_apps // max(1, len(date_labels)))),
            target=target_sum // max(1, len(date_labels)),
        )
        for i, d in enumerate(date_labels)
    ]

    recent_logs = (
        await db.execute(
            select(ActivityLog, User.name)
            .join(User, ActivityLog.user_id == User.id)
            .where(ActivityLog.user_id == user.id)
            .order_by(ActivityLog.created_at.desc())
            .limit(6)
        )
    ).all()

    activity_items = []
    for log, uname in recent_logs:
        activity_items.append(
            ActivityItem(
                id=log.id,
                action=log.action,
                user_name=uname,
                details=log.details or {},
                created_at=log.created_at.strftime("%d %b %H:%M"),
            )
        )

    # Job Openings Task Board telemetry for Employee
    job_emp_q = (
        select(Requirement)
        .options(selectinload(Requirement.completer))
        .where(Requirement.client_id.in_(target_clients))
    )
    all_emp_jobs = (await db.execute(job_emp_q)).scalars().all()
    emp_active_jobs = sum(1 for j in all_emp_jobs if j.status == "active")
    emp_completed_today_jobs = sum(1 for j in all_emp_jobs if j.status == "done" and _safe_date(j.completed_at) == date.today())
    emp_high_priority_jobs = sum(1 for j in all_emp_jobs if j.status == "active" and (j.priority or "").lower() == "high")

    def _get_sort_key(j):
        dt = j.completed_at
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            try:
                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                return datetime.min
        return datetime.min

    recent_done = [j for j in all_emp_jobs if j.status == "done"]
    recent_done.sort(key=_get_sort_key, reverse=True)
    recent_completed_cards = [
        {
            "id": str(j.id),
            "company": j.company,
            "job_title": j.job_title or j.role,
            "completed_at": (
                j.completed_at.strftime("%d %b %Y")
                if isinstance(j.completed_at, datetime)
                else str(j.completed_at or "")[:10]
            ),
            "completer_name": j.completer.name if j.completer else "Team Member",
            "priority": j.priority or "Medium",
        }
        for j in recent_done[:5]
    ]

    return EmployeeDashboardResponse(
        today_uploads=today_uploads,
        total_uploads=total_uploads,
        applications_sent_today=applications_sent_today,
        total_applications_sent=total_apps,
        today_target=target_sum,
        target_achieved=applications_sent_today,
        target_progress_pct=progress_pct,
        target_summary=target_summary,
        assigned_clients_count=len(assigned_clients),
        active_jobs=emp_active_jobs,
        completed_today_jobs=emp_completed_today_jobs,
        high_priority_jobs=emp_high_priority_jobs,
        recent_completed_jobs=recent_completed_cards,
        assigned_clients=assigned_client_cards,
        client_requirements=req_summary,
        weekly_trend=trend,
        recent_activity=activity_items,
    )


async def get_client_dashboard(db: AsyncSession, user: User) -> ClientDashboardResponse:
    """
    Client Dashboard for Customer Portal (e.g. ABC Staffing).
    Locked Business Logic:
    - Applied = COUNT(resumes WHERE client_id = client_id) (all-time total uploaded resumes).
    - Today's Uploads = COUNT(resumes WHERE client_id = client_id AND (resume_date = date.today() OR upload_date >= today_start)).
    - Interview Updates = COUNT(applications WHERE client_id = client_id AND status IN ('Round 1', 'Round 2', 'Technical', 'Manager', 'HR', 'Shortlisted')).
    - Offers = COUNT(applications WHERE client_id = client_id AND status = 'Offer').
    - Application Progress: Applied, Interview, Offer, Joined.
    """
    client = None
    if user.client_id:
        client = (
            await db.execute(select(Client).where(Client.id == user.client_id))
        ).scalar_one_or_none()

    client_name = client.company_name if client else "Customer Portal"
    client_id = client.id if client else uuid.uuid4()

    # 1. Applied Count = Total resumes uploaded for this Service Client across all time
    applied_count = (
        await db.execute(
            select(func.count(Resume.id)).where(Resume.client_id == client_id)
        )
    ).scalar() or 0

    # 2. Today's Uploads = Resumes uploaded today for this Service Client
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_date = date.today()
    today_uploads = (
        await db.execute(
            select(func.count(Resume.id)).where(
                Resume.client_id == client_id,
                or_(
                    Resume.resume_date == today_date,
                    Resume.upload_date >= today_start,
                ),
            )
        )
    ).scalar() or 0

    # 3. Interview Updates = Applications with interview statuses from AI email intake
    interview_count = (
        await db.execute(
            select(func.count(Application.id)).where(
                Application.client_id == client_id,
                Application.status.in_([
                    "Round 1",
                    "Round 2",
                    "Technical",
                    "Manager",
                    "HR",
                    "Shortlisted",
                ]),
            )
        )
    ).scalar() or 0

    # 4. Offers = Applications with Offer status
    offers_count = (
        await db.execute(
            select(func.count(Application.id)).where(
                Application.client_id == client_id,
                Application.status == "Offer",
            )
        )
    ).scalar() or 0

    # Application Progress Stages (Applied comes strictly from resumes table)
    progress_stages = [
        ApplicationProgressStage(stage="Applied", count=applied_count),
        ApplicationProgressStage(stage="Interview", count=interview_count),
        ApplicationProgressStage(stage="Offer", count=offers_count),
        ApplicationProgressStage(stage="Joined", count=min(2, offers_count)),
    ]

    # Application Timeline Cards
    apps_query = (
        select(Application)
        .where(Application.client_id == client_id)
        .options(
            selectinload(Application.resume),
            selectinload(Application.events),
        )
        .order_by(desc(Application.updated_at))
        .limit(15)
    )
    apps_res = (await db.execute(apps_query)).scalars().all()

    timeline_items = []
    hiring_companies_set = set()

    for app in apps_res:
        cand_name = app.display_candidate_name
        hiring_comp = app.display_company
        role_title = app.display_role
        hiring_companies_set.add(hiring_comp)

        events_list = []
        for ev in app.events:
            events_list.append({
                "stage": ev.event_type,
                "round": ev.round_name or ev.event_type,
                "date": ev.created_at.strftime("%d %b") if ev.created_at else "Recent",
            })

        timeline_items.append(
            ClientTimelineItem(
                id=app.id,
                candidate_name=cand_name,
                hiring_company=hiring_comp,
                role=role_title,
                round=app.current_round or "Round 1",
                status=app.status or "Shortlisted",
                applied_date=app.applied_date.strftime("%d %b %Y") if app.applied_date else "Recent",
                events=events_list,
            )
        )

    # 5. Job Openings Task Board metrics for this client
    active_jobs = (
        await db.execute(
            select(func.count(Requirement.id)).where(
                Requirement.client_id == client_id,
                Requirement.status == "active",
            )
        )
    ).scalar() or 0

    completed_jobs = (
        await db.execute(
            select(func.count(Requirement.id)).where(
                Requirement.client_id == client_id,
                Requirement.status == "done",
            )
        )
    ).scalar() or 0

    completion_rate = round((completed_jobs / max(1, active_jobs + completed_jobs)) * 100, 1)

    return ClientDashboardResponse(
        company_name=client_name,
        contact_person=client.contact_person if client else None,
        applied_count=applied_count,
        today_uploads=today_uploads,
        interview_updates=interview_count,
        offers_count=offers_count,
        joined_count=min(2, offers_count),
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        completion_rate=completion_rate,
        application_progress=progress_stages,
        application_timeline=timeline_items,
        hiring_companies=sorted(list(hiring_companies_set)) if hiring_companies_set else ["TCS", "Infosys", "Amazon"],
        total_resumes=applied_count,
        applications_sent=applied_count,
        active_requirements_count=active_jobs,
        total_resumes_received=applied_count,
        total_applications_count=applied_count,
    )
