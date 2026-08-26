import uuid
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, or_, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from app.modules.users.models import User
from app.modules.clients.models import Client, EmployeeClient
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
from app.modules.activity_logs.models import ActivityLog
from app.modules.resumes.parser import parse_resume_filename
from app.modules.resumes.schemas import (
    ResumeResponse,
    ParsedFileUploadItem,
    BulkUploadResponse,
    ConfirmManualUploadItem,
    UploadDashboardStats,
)
from app.services.google_drive import drive_service, UPLOAD_DIR


async def get_allowed_client_ids(db: AsyncSession, current_user: User) -> list[uuid.UUID] | None:
    """
    Returns allowed client IDs for current user.
    None means full access (Admin).
    """
    if current_user.role == "admin":
        return None
    elif current_user.role == "sub_admin":
        from app.modules.users.service import get_sub_admin_client_ids
        return await get_sub_admin_client_ids(db, current_user.id)
    elif current_user.role == "employee":
        result = await db.execute(
            select(EmployeeClient.client_id).where(
                EmployeeClient.employee_id == current_user.id,
                EmployeeClient.active == True,
            )
        )
        return list(result.scalars().all())
    elif current_user.role == "client":
        return [current_user.client_id] if current_user.client_id else []
    return []


async def get_unique_companies(db: AsyncSession, current_user: User) -> list[str]:
    """Get list of distinct company names across accessible resumes for dropdown filter."""
    allowed_clients = await get_allowed_client_ids(db, current_user)
    query = select(distinct(Resume.company)).where(Resume.company.isnot(None))

    if allowed_clients is not None:
        query = query.where(Resume.client_id.in_(allowed_clients))

    result = await db.execute(query)
    companies = [c for c in result.scalars().all() if c and c.strip()]
    return sorted(list(set(companies)))


async def check_duplicates(
    db: AsyncSession, client_id: uuid.UUID, items: list[dict]
) -> list[dict]:
    """Check batch of items against existing DB resumes to identify duplicates."""
    results = []
    for item in items:
        company = item.get("company", "").strip()
        candidate = item.get("candidate_name", "").strip()
        tag = item.get("resume_id_tag", "").strip() if item.get("resume_id_tag") else None

        query = select(Resume).where(
            Resume.client_id == client_id,
            Resume.company.ilike(company) if company else True,
        )
        if tag:
            query = query.where(
                or_(
                    Resume.resume_id_tag.ilike(tag),
                    Resume.candidate_name.ilike(candidate) if candidate else False,
                )
            )
        elif candidate:
            query = query.where(Resume.candidate_name.ilike(candidate))

        match = (await db.execute(query)).scalar_one_or_none()
        is_dup = match is not None

        results.append({
            "filename": item.get("filename"),
            "is_duplicate": is_dup,
            "duplicate_resume_id": str(match.id) if match else None,
            "existing_candidate": match.candidate_name if match else None,
            "existing_company": match.company if match else None,
        })
    return results


async def search_resumes(
    db: AsyncSession,
    current_user: User,
    search: str | None = None,
    client_id: uuid.UUID | None = None,
    requirement_id: uuid.UUID | None = None,
    company: str | None = None,
    role: str | None = None,
    candidate_name: str | None = None,
    resume_id_tag: str | None = None,
    resume_date: date | None = None,
    date_filter: str | None = None,
    custom_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ResumeResponse], int]:
    """Search resumes with strict role/assignment scoping and global date filtering."""
    allowed_clients = await get_allowed_client_ids(db, current_user)

    query = (
        select(Resume, Client.company_name, User.name, Requirement.role_code)
        .join(Client, Resume.client_id == Client.id)
        .join(User, Resume.uploaded_by == User.id)
        .outerjoin(Requirement, Resume.requirement_id == Requirement.id)
    )

    if allowed_clients is not None:
        query = query.where(Resume.client_id.in_(allowed_clients))

    if client_id:
        if allowed_clients is not None and client_id not in allowed_clients:
            return [], 0
        query = query.where(Resume.client_id == client_id)

    if requirement_id:
        query = query.where(Resume.requirement_id == requirement_id)

    if company:
        query = query.where(Resume.company.ilike(f"%{company.strip()}%"))

    if role:
        query = query.where(Resume.role.ilike(f"%{role.strip()}%"))

    if candidate_name:
        query = query.where(Resume.candidate_name.ilike(f"%{candidate_name.strip()}%"))

    if resume_id_tag:
        query = query.where(Resume.resume_id_tag.ilike(f"%{resume_id_tag.strip()}%"))

    # Global Date Filtering on resume_date
    target_d = custom_date or resume_date
    today_val = date.today()

    if date_filter in ("today", "Today"):
        query = query.where(
            or_(
                Resume.resume_date == today_val,
                func.date(Resume.upload_date) == today_val,
            )
        )
    elif date_filter in ("yesterday", "Yesterday"):
        y_val = today_val - timedelta(days=1)
        query = query.where(
            or_(
                Resume.resume_date == y_val,
                func.date(Resume.upload_date) == y_val,
            )
        )
    elif date_filter in ("this_week", "This Week"):
        w_start = today_val - timedelta(days=today_val.weekday())
        query = query.where(
            or_(
                (Resume.resume_date >= w_start) & (Resume.resume_date <= today_val),
                (func.date(Resume.upload_date) >= w_start) & (func.date(Resume.upload_date) <= today_val),
            )
        )
    elif date_filter in ("this_month", "This Month"):
        m_start = date(today_val.year, today_val.month, 1)
        query = query.where(
            or_(
                (Resume.resume_date >= m_start) & (Resume.resume_date <= today_val),
                (func.date(Resume.upload_date) >= m_start) & (func.date(Resume.upload_date) <= today_val),
            )
        )
    elif target_d:
        query = query.where(
            or_(
                Resume.resume_date == target_d,
                func.date(Resume.upload_date) == target_d,
            )
        )
    elif start_date and end_date:
        query = query.where(
            or_(
                (Resume.resume_date >= start_date) & (Resume.resume_date <= end_date),
                (func.date(Resume.upload_date) >= start_date) & (func.date(Resume.upload_date) <= end_date),
            )
        )
    elif start_date:
        query = query.where(
            or_(
                Resume.resume_date >= start_date,
                func.date(Resume.upload_date) >= start_date,
            )
        )
    elif end_date:
        query = query.where(
            or_(
                Resume.resume_date <= end_date,
                func.date(Resume.upload_date) <= end_date,
            )
        )

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Resume.candidate_name.ilike(search_term),
                Resume.company.ilike(search_term),
                Resume.role.ilike(search_term),
                Resume.resume_id_tag.ilike(search_term),
                Client.company_name.ilike(search_term),
                Resume.original_filename.ilike(search_term),
                Requirement.role_code.ilike(search_term),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Resume.upload_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # Get application status for these resumes
    resume_ids = [r[0].id for r in rows]
    has_app_set = set()
    if resume_ids:
        app_res = await db.execute(
            select(Application.resume_id).where(Application.resume_id.in_(resume_ids))
        )
        has_app_set = set(app_res.scalars().all())

    response_items = []
    for resume, client_name, uploader_name, req_code in rows:
        # Note visibility check for client user
        notes_visible = resume.client_notes
        if current_user.role == "client" and not resume.is_note_shared:
            notes_visible = None

        response_items.append(
            ResumeResponse(
                id=resume.id,
                display_id=resume.display_id,
                candidate_name=resume.candidate_name,
                company=resume.company or "General",
                role=resume.role,
                resume_id_tag=resume.resume_id_tag,
                requirement_id=resume.requirement_id,
                requirement_code=req_code,
                client_id=resume.client_id,
                client_name=client_name,
                uploaded_by=resume.uploaded_by,
                uploader_name=uploader_name,
                original_filename=resume.original_filename,
                resume_date=resume.resume_date,
                client_notes=notes_visible,
                is_note_shared=resume.is_note_shared,
                drive_file_id=resume.drive_file_id,
                drive_url=f"https://drive.google.com/file/d/{resume.drive_file_id}/view" if resume.drive_file_id and not resume.drive_file_id.startswith("file_") else None,
                upload_date=resume.upload_date,
                has_application=resume.id in has_app_set,
            )
        )

    return response_items, total_count


async def delete_resume(db: AsyncSession, resume_id: uuid.UUID, current_user: User) -> dict:
    """Delete a resume: Admin (all), Sub-Admin (assigned clients), Employee (own uploads)."""
    resume = (
        await db.execute(select(Resume).where(Resume.id == resume_id))
    ).scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if current_user.role == "admin":
        pass
    elif current_user.role == "sub_admin":
        allowed_cids = await get_allowed_client_ids(db, current_user)
        if allowed_cids is not None and resume.client_id not in allowed_cids:
            raise HTTPException(status_code=403, detail="Forbidden: Resume is outside your management scope.")
    elif current_user.role == "employee":
        if resume.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden: You can only delete your own uploads.")
    else:
        raise HTTPException(status_code=403, detail="Forbidden: Clients cannot delete resumes.")

    if resume.drive_file_id:
        try:
            await drive_service.delete_file(resume.drive_file_id)
        except Exception:
            pass

    # Delete associated applications
    await db.execute(
        delete(Application).where(Application.resume_id == resume_id)
    )
    await db.delete(resume)

    from app.modules.activity_logs.models import ActivityLog
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="resume_deleted",
            details={"resume_id": str(resume_id), "candidate_name": resume.candidate_name},
        )
    )
    await db.flush()

    return {"message": "Resume deleted successfully from database and Google Drive."}


async def update_resume(
    db: AsyncSession, resume_id: uuid.UUID, payload: ResumeUpdate, current_user: User
) -> Resume:
    resume = await get_resume_by_id(db, resume_id, current_user)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if current_user.role == "employee" and resume.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only edit your own uploads.")

    if payload.candidate_name is not None:
        resume.candidate_name = payload.candidate_name.strip()
    if payload.company is not None:
        resume.company = payload.company.strip()
    if payload.role is not None:
        resume.role = payload.role.strip()
    if payload.client_id is not None:
        allowed_clients = await get_allowed_client_ids(db, current_user)
        if allowed_clients is not None and payload.client_id not in allowed_clients:
            raise HTTPException(status_code=403, detail="Forbidden: Target client is outside your scope.")
        resume.client_id = payload.client_id
    if payload.requirement_id is not None:
        resume.requirement_id = payload.requirement_id
    if payload.resume_date is not None:
        resume.resume_date = payload.resume_date
    if payload.client_notes is not None:
        resume.client_notes = payload.client_notes
    if payload.is_note_shared is not None:
        resume.is_note_shared = payload.is_note_shared

    from app.modules.activity_logs.models import ActivityLog
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="resume_updated",
            details={"resume_id": str(resume.id), "candidate_name": resume.candidate_name},
        )
    )
    await db.flush()
    return resume


async def dispatch_upload_notifications_and_stats(
    db: AsyncSession,
    current_user: User,
    client: Client,
    saved_count: int,
    batch_date: date,
) -> UploadDashboardStats:
    """Auto-sync workflow: Activity Log + Multi-Role In-App Notifications + Live Stats."""
    from app.modules.notifications.models import Notification
    from app.modules.users.models import SubAdminAssignment
    from app.modules.activity_logs.models import ActivityLog
    from datetime import datetime

    # 1. Activity Log for batch
    db.add(
        ActivityLog(
            user_id=current_user.id,
            action="resume_batch_uploaded",
            details={
                "client_id": str(client.id),
                "client_name": client.company_name,
                "saved_count": saved_count,
                "resume_date": batch_date.isoformat(),
            },
        )
    )

    # 2. Notification to Employee (Uploader)
    db.add(
        Notification(
            user_id=current_user.id,
            title="Upload Completed",
            message=f"Successfully uploaded {saved_count} candidate resumes for {client.company_name}.",
            type="upload_completed",
        )
    )

    # 3. Notification to Admins
    admin_users = (
        await db.execute(select(User).where(User.role == "admin", User.is_active == True))
    ).scalars().all()
    for admin in admin_users:
        if admin.id != current_user.id:
            db.add(
                Notification(
                    user_id=admin.id,
                    title="New Resumes Uploaded",
                    message=f"{current_user.name} uploaded {saved_count} resumes to {client.company_name}.",
                    type="upload_completed",
                )
            )

    # 4. Notification to Sub-Admins assigned to this client
    sub_admin_assignments = (
        await db.execute(
            select(SubAdminAssignment.sub_admin_id).where(
                SubAdminAssignment.client_id == client.id
            )
        )
    ).scalars().all()
    for sub_admin_id in set(sub_admin_assignments):
        if sub_admin_id != current_user.id:
            db.add(
                Notification(
                    user_id=sub_admin_id,
                    title="New Resumes Ingested",
                    message=f"New resumes uploaded: {current_user.name} uploaded {saved_count} resumes to {client.company_name}.",
                    type="upload_completed",
                )
            )

    # 5. Notification to Client Portal Users
    client_users = (
        await db.execute(
            select(User).where(
                User.client_id == client.id,
                User.is_active == True,
            )
        )
    ).scalars().all()
    for c_user in client_users:
        db.add(
            Notification(
                user_id=c_user.id,
                title="New Candidates Available",
                message=f"{saved_count} new candidate resumes are available in your portal.",
                type="resume_available",
            )
        )

    await db.flush()

    # Calculate live dashboard statistics for employee
    today_date = date.today()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    today_uploads = (
        await db.execute(
            select(func.count(Resume.id)).where(
                Resume.uploaded_by == current_user.id,
                or_(
                    Resume.resume_date == today_date,
                    Resume.upload_date >= today_start,
                ),
            )
        )
    ).scalar() or 0

    total_resumes = (
        await db.execute(
            select(func.count(Resume.id)).where(Resume.uploaded_by == current_user.id)
        )
    ).scalar() or 0

    return UploadDashboardStats(
        today_uploads=today_uploads,
        total_resumes=total_resumes,
    )


async def process_bulk_upload(
    db: AsyncSession,
    current_user: User,
    files: list[UploadFile],
    client_id: uuid.UUID,
    resume_date: date | None = None,
    requirement_id: uuid.UUID | None = None,
) -> BulkUploadResponse:
    """
    Process bulk PDF upload into selected Service Client:
    - Validate employee is assigned to Client
    - Parse filename for Company, Role, Candidate / Resume ID
    - Store PDF in Drive / local storage and metadata in DB
    - Auto-sync to client, update dashboards, create activity logs and notifications
    """
    allowed_clients = await get_allowed_client_ids(db, current_user)

    if allowed_clients is not None and client_id not in allowed_clients:
        raise HTTPException(
            status_code=403,
            detail="Permission Denied: You are not assigned to this Service Client.",
        )

    client = (
        await db.execute(select(Client).where(Client.id == client_id))
    ).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Service Client not found")

    selected_req = None
    if requirement_id:
        selected_req = (
            await db.execute(
                select(Requirement).where(
                    Requirement.id == requirement_id,
                    Requirement.client_id == client_id,
                )
            )
        ).scalar_one_or_none()

    batch_date = resume_date or date.today()

    items = []
    saved_count = 0
    needs_review_count = 0
    rejected_count = 0

    # Read and parse files
    tasks_to_upload = []
    for file in files:
        filename = file.filename or "resume.pdf"
        file_bytes = await file.read()
        parsed = parse_resume_filename(filename, selected_client_name=client.company_name)

        target_company = parsed.get("company") or (selected_req.company if selected_req else "General")
        target_role = parsed.get("role") or (selected_req.role if selected_req else "General Role")
        candidate_name = parsed.get("candidate_name") or "Candidate"

        if not parsed["success"] or parsed.get("confidence") == "low":
            temp_id = f"tmp_{uuid.uuid4().hex}"
            temp_path = UPLOAD_DIR / f"{temp_id}_{filename}"
            with open(temp_path, "wb") as f:
                f.write(file_bytes)

            items.append(
                ParsedFileUploadItem(
                    filename=filename,
                    status="needs_review",
                    message=parsed.get("error") or "Metadata requires review before saving.",
                    company=target_company,
                    role=target_role,
                    candidate_name=candidate_name,
                    resume_id_tag=parsed.get("resume_id_tag"),
                    client_name=client.company_name,
                    client_id=client.id,
                    requirement_id=selected_req.id if selected_req else None,
                    requirement_code=selected_req.role_code if selected_req else None,
                    resume_date=batch_date,
                    temp_file_id=temp_id,
                )
            )
            needs_review_count += 1
        else:
            tasks_to_upload.append((file_bytes, filename, parsed, target_company, target_role, candidate_name))

    # Upload valid files concurrently
    import asyncio
    sem = asyncio.Semaphore(10)

    async def upload_task(item_data):
        f_bytes, f_name, f_parsed, t_comp, t_role, c_name = item_data
        async with sem:
            upload_res = await drive_service.upload_file(
                file_bytes=f_bytes,
                filename=f_name,
                client_name=client.company_name,
            )
            return f_bytes, f_name, f_parsed, t_comp, t_role, c_name, upload_res

    if tasks_to_upload:
        upload_results = await asyncio.gather(*[upload_task(t) for t in tasks_to_upload])
        from app.modules.activity_logs.models import ActivityLog
        for f_bytes, f_name, f_parsed, t_comp, t_role, c_name, upload_res in upload_results:
            resume = Resume(
                candidate_name=c_name,
                company=t_comp,
                role=t_role,
                resume_id_tag=f_parsed.get("resume_id_tag"),
                client_id=client.id,
                requirement_id=selected_req.id if selected_req else None,
                uploaded_by=current_user.id,
                resume_date=batch_date,
                drive_file_id=upload_res.get("drive_file_id"),
                original_filename=f_name,
            )
            db.add(resume)
            await db.flush()

            # Also create corresponding Application in candidate pipeline for real-time target quota tracking
            from app.modules.applications.models import Application, ApplicationEvent
            now_dt = datetime.now(timezone.utc)
            app_applied_date = datetime.combine(batch_date, now_dt.time()).replace(tzinfo=timezone.utc) if batch_date else now_dt

            application = Application(
                resume_id=resume.id,
                candidate_name=c_name,
                company=t_comp,
                role=t_role,
                requirement_id=selected_req.id if selected_req else None,
                employee_id=current_user.id,
                client_id=client.id,
                status="Submitted",
                current_round="Initial Application",
                applied_date=app_applied_date,
            )
            db.add(application)
            await db.flush()

            db.add(
                ApplicationEvent(
                    application_id=application.id,
                    event_type="Submitted",
                    round_name="Initial Application",
                    created_by=current_user.id,
                    created_at=app_applied_date,
                )
            )

            # Log activity per candidate
            db.add(
                ActivityLog(
                    user_id=current_user.id,
                    action="resume_uploaded",
                    details={
                        "resume_id": str(resume.id),
                        "application_id": str(application.id),
                        "client": client.company_name,
                        "company": t_comp,
                        "candidate": c_name,
                        "resume_date": batch_date.isoformat(),
                    },
                )
            )

            items.append(
                ParsedFileUploadItem(
                    filename=f_name,
                    status="saved",
                    message="Successfully parsed and saved to database & storage.",
                    company=t_comp,
                    role=t_role,
                    candidate_name=c_name,
                    resume_id_tag=resume.resume_id_tag,
                    client_name=client.company_name,
                    client_id=client.id,
                    requirement_id=selected_req.id if selected_req else None,
                    requirement_code=selected_req.role_code if selected_req else None,
                    resume_date=batch_date,
                    drive_file_id=resume.drive_file_id,
                    saved_resume_id=resume.id,
                )
            )
            saved_count += 1

    # Auto-Sync Notifications & Dashboard Telemetry
    dash_stats = None
    if saved_count > 0:
        dash_stats = await dispatch_upload_notifications_and_stats(
            db=db,
            current_user=current_user,
            client=client,
            saved_count=saved_count,
            batch_date=batch_date,
        )

    return BulkUploadResponse(
        success=True,
        total_files=len(files),
        saved_count=saved_count,
        uploaded=saved_count,
        needs_review_count=needs_review_count,
        rejected_count=rejected_count,
        client_synced=True,
        dashboard=dash_stats,
        items=items,
    )


async def confirm_manual_uploads(
    db: AsyncSession,
    current_user: User,
    items: list[ConfirmManualUploadItem],
) -> list[ResumeResponse]:
    allowed_clients = await get_allowed_client_ids(db, current_user)
    saved_resumes = []
    last_client = None

    for item in items:
        if allowed_clients is not None and item.client_id not in allowed_clients:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: You are not assigned to Service Client ID {item.client_id}",
            )

        client = (
            await db.execute(select(Client).where(Client.id == item.client_id))
        ).scalar_one_or_none()
        if not client:
            continue
        last_client = client

        file_bytes = b""
        if item.temp_file_id:
            temp_path = UPLOAD_DIR / f"{item.temp_file_id}_{item.original_filename}"
            if temp_path.is_file():
                with open(temp_path, "rb") as f:
                    file_bytes = f.read()
                try:
                    temp_path.unlink()
                except Exception:
                    pass

        upload_res = await drive_service.upload_file(
            file_bytes=file_bytes or b"%PDF-1.4...",
            filename=item.original_filename,
            client_name=client.company_name,
        )

        resume = Resume(
            candidate_name=item.candidate_name.strip(),
            company=item.company.strip() if item.company else "General",
            role=item.role.strip(),
            resume_id_tag=item.resume_id_tag,
            client_id=client.id,
            requirement_id=item.requirement_id,
            uploaded_by=current_user.id,
            resume_date=item.resume_date or date.today(),
            client_notes=item.client_notes,
            drive_file_id=upload_res.get("drive_file_id"),
            original_filename=item.original_filename,
        )
        db.add(resume)
        await db.flush()

        from app.modules.applications.models import Application, ApplicationEvent
        now_dt = datetime.now(timezone.utc)
        app_date = item.resume_date or date.today()
        app_applied_date = datetime.combine(app_date, now_dt.time()).replace(tzinfo=timezone.utc)

        application = Application(
            resume_id=resume.id,
            candidate_name=resume.candidate_name,
            company=resume.company,
            role=resume.role,
            requirement_id=item.requirement_id,
            employee_id=current_user.id,
            client_id=client.id,
            status="Submitted",
            current_round="Initial Application",
            applied_date=app_applied_date,
        )
        db.add(application)
        await db.flush()

        db.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="Submitted",
                round_name="Initial Application",
                created_by=current_user.id,
                created_at=app_applied_date,
            )
        )

        saved_resumes.append(
            ResumeResponse(
                id=resume.id,
                display_id=resume.display_id,
                candidate_name=resume.candidate_name,
                company=resume.company,
                role=resume.role,
                resume_id_tag=resume.resume_id_tag,
                requirement_id=resume.requirement_id,
                client_id=client.id,
                client_name=client.company_name,
                uploaded_by=current_user.id,
                uploader_name=current_user.name,
                original_filename=resume.original_filename,
                resume_date=resume.resume_date,
                client_notes=resume.client_notes,
                is_note_shared=resume.is_note_shared,
                upload_date=resume.upload_date,
            )
        )

    if saved_resumes and last_client:
        await dispatch_upload_notifications_and_stats(
            db=db,
            current_user=current_user,
            client=last_client,
            saved_count=len(saved_resumes),
            batch_date=date.today(),
        )

    return saved_resumes


async def get_resume_by_id(
    db: AsyncSession, resume_id: uuid.UUID, current_user: User
) -> Resume | None:
    allowed_clients = await get_allowed_client_ids(db, current_user)
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        return None

    if allowed_clients is not None and resume.client_id not in allowed_clients:
        raise HTTPException(status_code=403, detail="Access denied for this resume.")
    return resume


async def find_matching_resume(
    db: AsyncSession,
    client_id: uuid.UUID,
    candidate_name: str | None = None,
    company: str | None = None,
    role: str | None = None,
    resume_id_tag: str | None = None,
) -> FindResumeMatchResponse:
    """
    Smart Resume Linking matching logic (Priority 1 -> 2 -> 3 -> 4).
    Search ONLY within the specified client_id. Never cross-search other clients.
    """
    from app.modules.resumes.schemas import FindResumeMatchResponse

    if not client_id:
        return FindResumeMatchResponse(matched=False)

    cand_name_clean = (candidate_name or "").strip()
    company_clean = (company or "").strip()
    role_clean = (role or "").strip()
    tag_clean = (resume_id_tag or "").strip()

    # Priority 1: Resume ID Match
    if tag_clean:
        clean_tag = tag_clean.upper().replace("-", "").replace("_", "")
        stmt_p1 = select(Resume).where(
            Resume.client_id == client_id,
            or_(
                Resume.resume_id_tag.ilike(f"%{clean_tag}%"),
                Resume.resume_id_tag.ilike(f"%{tag_clean}%"),
                Resume.original_filename.ilike(f"%{clean_tag}%"),
                Resume.original_filename.ilike(f"%{tag_clean}%"),
            ),
        )
        res_p1 = (await db.execute(stmt_p1)).scalars().first()
        if res_p1:
            return FindResumeMatchResponse(
                matched=True,
                resume_id=res_p1.id,
                resume_name=res_p1.original_filename,
                candidate_name=res_p1.candidate_name,
                company=res_p1.company,
                role=res_p1.role,
                resume_id_tag=res_p1.resume_id_tag,
                match_priority=1,
                match_reason=f"Matched by Resume ID ({tag_clean})",
            )

    # Priority 2: Candidate Name + Company
    if cand_name_clean and company_clean:
        stmt_p2 = select(Resume).where(
            Resume.client_id == client_id,
            Resume.candidate_name.ilike(f"%{cand_name_clean}%"),
            Resume.company.ilike(f"%{company_clean}%"),
        )
        res_p2 = (await db.execute(stmt_p2)).scalars().first()
        if res_p2:
            return FindResumeMatchResponse(
                matched=True,
                resume_id=res_p2.id,
                resume_name=res_p2.original_filename,
                candidate_name=res_p2.candidate_name,
                company=res_p2.company,
                role=res_p2.role,
                resume_id_tag=res_p2.resume_id_tag,
                match_priority=2,
                match_reason=f"Matched by Candidate Name ({cand_name_clean}) + Company ({company_clean})",
            )

    # Priority 3: Candidate Name + Role
    if cand_name_clean and role_clean:
        stmt_p3 = select(Resume).where(
            Resume.client_id == client_id,
            Resume.candidate_name.ilike(f"%{cand_name_clean}%"),
            Resume.role.ilike(f"%{role_clean}%"),
        )
        res_p3 = (await db.execute(stmt_p3)).scalars().first()
        if res_p3:
            return FindResumeMatchResponse(
                matched=True,
                resume_id=res_p3.id,
                resume_name=res_p3.original_filename,
                candidate_name=res_p3.candidate_name,
                company=res_p3.company,
                role=res_p3.role,
                resume_id_tag=res_p3.resume_id_tag,
                match_priority=3,
                match_reason=f"Matched by Candidate Name ({cand_name_clean}) + Role ({role_clean})",
            )

    # Priority 4: No Match
    return FindResumeMatchResponse(
        matched=False,
        resume_id=None,
        resume_name=None,
        match_priority=None,
        match_reason="No matching resume found in client candidate bank.",
    )
