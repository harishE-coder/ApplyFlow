import io
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.requirements.models import Requirement
from app.modules.resumes.models import Resume
from app.modules.applications.models import Application
import pandas as pd


async def generate_excel_report(
    db: AsyncSession,
    current_user: User | None = None,
    client_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
) -> bytes:
    """Generate multi-sheet Excel recruitment report matching Customer & Requirements model."""
    from app.modules.users.service import get_sub_admin_client_ids, get_sub_admin_employee_ids

    allowed_client_ids = None
    allowed_employee_ids = None
    if current_user and current_user.role == "sub_admin":
        allowed_client_ids = await get_sub_admin_client_ids(db, current_user.id)
        allowed_employee_ids = await get_sub_admin_employee_ids(db, current_user.id)

    # 1. Fetch Requirements with batch counts
    req_query = select(Requirement, Client.company_name).join(Client, Requirement.client_id == Client.id)
    if allowed_client_ids is not None:
        req_query = req_query.where(Requirement.client_id.in_(allowed_client_ids))
    if client_id:
        req_query = req_query.where(Requirement.client_id == client_id)
    reqs_res = await db.execute(req_query)
    raw_reqs = reqs_res.all()

    # Pre-fetch counts in single queries
    res_counts_map = dict((await db.execute(
        select(Resume.requirement_id, func.count(Resume.id)).where(Resume.requirement_id.is_not(None)).group_by(Resume.requirement_id)
    )).all())
    app_counts_map = dict((await db.execute(
        select(Application.requirement_id, func.count(Application.id)).where(Application.requirement_id.is_not(None)).group_by(Application.requirement_id)
    )).all())

    reqs_data = []
    for r, client_name in raw_reqs:
        res_count = res_counts_map.get(r.id, 0)
        app_count = app_counts_map.get(r.id, 0)
        reqs_data.append({
            "Requirement Code": r.role_code,
            "Client Customer": client_name,
            "Target Company": r.company,
            "Job Role": r.role,
            "Status": r.status.capitalize(),
            "Total Resumes": res_count,
            "Applications Submitted": app_count,
            "Created Date": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
        })

    # 2. Fetch Resumes
    r_query = (
        select(Resume, Client.company_name, User.name, Requirement.role_code)
        .join(Client, Resume.client_id == Client.id)
        .join(User, Resume.uploaded_by == User.id)
        .outerjoin(Requirement, Resume.requirement_id == Requirement.id)
    )
    if allowed_client_ids is not None:
        r_query = r_query.where(Resume.client_id.in_(allowed_client_ids))
    if allowed_employee_ids is not None:
        r_query = r_query.where(Resume.uploaded_by.in_(allowed_employee_ids))
    if client_id:
        r_query = r_query.where(Resume.client_id == client_id)
    if employee_id:
        r_query = r_query.where(Resume.uploaded_by == employee_id)

    resumes_res = await db.execute(r_query)
    resumes_data = [
        {
            "Resume ID": r.display_id,
            "Candidate Name": r.candidate_name,
            "Target Company": r.company,
            "Role": r.role,
            "Requirement Code": req_code or "N/A",
            "Client Customer": client_name,
            "Uploaded By": uploader_name,
            "Original Filename": r.original_filename,
            "Upload Date": r.upload_date.strftime("%Y-%m-%d %H:%M") if r.upload_date else "",
        }
        for r, client_name, uploader_name, req_code in resumes_res.all()
    ]

    # 3. Fetch Applications
    a_query = (
        select(Application, Resume, Client.company_name, User.name, Requirement.role_code)
        .outerjoin(Resume, Application.resume_id == Resume.id)
        .outerjoin(Client, Application.client_id == Client.id)
        .outerjoin(User, Application.employee_id == User.id)
        .outerjoin(Requirement, Application.requirement_id == Requirement.id)
    )
    if allowed_client_ids is not None:
        a_query = a_query.where(Application.client_id.in_(allowed_client_ids))
    if allowed_employee_ids is not None:
        a_query = a_query.where(Application.employee_id.in_(allowed_employee_ids))
    if client_id:
        a_query = a_query.where(Application.client_id == client_id)
    if employee_id:
        a_query = a_query.where(Application.employee_id == employee_id)

    apps_res = await db.execute(a_query)
    apps_data = [
        {
            "Application ID": str(app.id)[:8],
            "Resume ID": resume.display_id if resume else "N/A",
            "Candidate Name": resume.candidate_name if resume else (app.candidate_name or "N/A"),
            "Target Company": resume.company if resume else (app.company or "N/A"),
            "Role": resume.role if resume else (app.role or "N/A"),
            "Requirement Code": req_code or "N/A",
            "Client Customer": client_name or "N/A",
            "Submitted By": emp_name or "N/A",
            "Status": (app.status or "Submitted").capitalize(),
            "Applied Date": app.applied_date.strftime("%Y-%m-%d %H:%M") if app.applied_date else "",
        }
        for app, resume, client_name, emp_name, req_code in apps_res.all()
    ]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_apps = pd.DataFrame(apps_data) if apps_data else pd.DataFrame([{"Info": "No applications"}])
        df_reqs = pd.DataFrame(reqs_data) if reqs_data else pd.DataFrame([{"Info": "No requirements"}])
        df_resumes = pd.DataFrame(resumes_data) if resumes_data else pd.DataFrame([{"Info": "No resumes"}])

        df_apps.to_excel(writer, sheet_name="Applications", index=False)
        df_reqs.to_excel(writer, sheet_name="Client Requirements", index=False)
        df_resumes.to_excel(writer, sheet_name="Resumes Catalog", index=False)

    return output.getvalue()


async def generate_pdf_report(
    db: AsyncSession,
    current_user: User | None = None,
    client_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
) -> bytes:
    """Generate branded PDF recruitment summary report using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    navy = colors.HexColor("#0A1B3D")
    bright_blue = colors.HexColor("#0D6EFD")
    surface = colors.HexColor("#F5F7FA")

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=navy,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=bright_blue,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=navy,
        spaceBefore=10,
        spaceAfter=6,
    )

    story = []
    story.append(Paragraph("<b>Apply Flow Careers</b> — Client Recruitment Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now(timezone.utc).strftime('%d %B %Y, %H:%M UTC')} | Confidential Corporate Summary", subtitle_style))
    story.append(Spacer(1, 8))

    from app.modules.users.service import get_sub_admin_client_ids, get_sub_admin_employee_ids

    allowed_client_ids = None
    allowed_employee_ids = None
    if current_user and current_user.role == "sub_admin":
        allowed_client_ids = await get_sub_admin_client_ids(db, current_user.id)
        allowed_employee_ids = await get_sub_admin_employee_ids(db, current_user.id)

    # Applications table
    a_query = (
        select(Application, Resume, Client.company_name, User.name, Requirement.role_code)
        .outerjoin(Resume, Application.resume_id == Resume.id)
        .outerjoin(Client, Application.client_id == Client.id)
        .outerjoin(User, Application.employee_id == User.id)
        .outerjoin(Requirement, Application.requirement_id == Requirement.id)
        .order_by(Application.applied_date.desc())
        .limit(20)
    )
    if allowed_client_ids is not None:
        a_query = a_query.where(Application.client_id.in_(allowed_client_ids))
    if allowed_employee_ids is not None:
        a_query = a_query.where(Application.employee_id.in_(allowed_employee_ids))
    if client_id:
        a_query = a_query.where(Application.client_id == client_id)
    if employee_id:
        a_query = a_query.where(Application.employee_id == employee_id)

    apps_res = await db.execute(a_query)
    rows = apps_res.all()

    story.append(Paragraph("Recent Candidate Submissions by Requirement", section_style))

    table_data = [["ID", "Candidate", "Company", "Role", "Req Code", "Client", "Status"]]
    for app, resume, c_name, u_name, req_code in rows:
        disp_id = resume.display_id if resume else str(app.id)[:8]
        cand_name = (resume.candidate_name if resume else (app.candidate_name or "N/A"))[:16]
        comp = (resume.company if resume else (app.company or "N/A"))[:10]
        role_str = (resume.role if resume else (app.role or "N/A"))[:14]
        table_data.append([
            disp_id,
            cand_name,
            comp,
            role_str,
            req_code or "N/A",
            (c_name or "N/A")[:12],
            (app.status or "Submitted").capitalize(),
        ])

    if len(table_data) == 1:
        table_data.append(["-", "No records found", "-", "-", "-", "-", "-"])

    t = Table(table_data, colWidths=[55, 105, 75, 95, 75, 80, 55])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, surface]),
            ("TEXTCOLOR", (0, 1), (-1, -1), navy),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ])
    )
    story.append(t)

    doc.build(story)
    return buffer.getvalue()


async def export_clients_csv(db: AsyncSession, current_user: User, status: str = "active") -> str:
    from app.modules.clients import service as client_service
    clients = await client_service.get_clients(db, current_user, status_filter=status)
    rows = [
        {
            "Client Name": c.company_name,
            "Contact Person": c.contact_person or "",
            "Email": c.email or "",
            "Phone": c.phone or "",
            "Status": c.status,
            "Total Requirements": c.total_requirements,
            "Active Requirements": c.active_requirements,
            "Total Resumes": c.total_resumes,
            "Created Date": c.created_at.strftime("%Y-%m-%d") if c.created_at else "",
        }
        for c in clients
    ]
    df = pd.DataFrame(rows, columns=[
        "Client Name", "Contact Person", "Email", "Phone", "Status",
        "Total Requirements", "Active Requirements", "Total Resumes", "Created Date"
    ])
    return df.to_csv(index=False)


async def export_employees_csv(db: AsyncSession, current_user: User, status: str = "inactive") -> str:
    from app.modules.users import service as user_service
    users = await user_service.get_users(db, current_user, role="employee", status_filter=status)
    rows = [
        {
            "Employee Name": u.name,
            "Email": u.email,
            "Status": u.status,
            "Assigned Clients": ", ".join([c.company_name for c in u.assigned_clients]),
            "Created Date": u.created_at.strftime("%Y-%m-%d") if u.created_at else "",
        }
        for u in users
    ]
    df = pd.DataFrame(rows, columns=[
        "Employee Name", "Email", "Status", "Assigned Clients", "Created Date"
    ])
    return df.to_csv(index=False)


async def export_targets_csv(db: AsyncSession, current_user: User, status: str = "ended") -> str:
    from app.modules.targets import service as target_service
    targets = await target_service.get_targets(db, current_user)
    if status != "all":
        targets = [t for t in targets if t.status == status]
    rows = [
        {
            "Employee Name": t.employee_name,
            "Client Name": t.client_name,
            "Daily Target": t.daily_target,
            "Status": t.status,
            "Effective Date": t.effective_date.strftime("%Y-%m-%d") if t.effective_date else "",
        }
        for t in targets
    ]
    df = pd.DataFrame(rows, columns=[
        "Employee Name", "Client Name", "Daily Target", "Status", "Effective Date"
    ])
    return df.to_csv(index=False)
