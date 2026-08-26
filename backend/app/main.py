"""
Apply Flow Careers — FastAPI application entry point.
Registers all routers, middleware, and imports models for Alembic.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# ---- Import all models so SQLAlchemy registers them ----
from app.modules.users.models import User, SubAdminAssignment  # noqa: F401
from app.modules.clients.models import Client, EmployeeClient  # noqa: F401
from app.modules.requirements.models import Requirement  # noqa: F401
from app.modules.resumes.models import Resume  # noqa: F401
from app.modules.applications.models import Application, ApplicationEvent  # noqa: F401
from app.modules.targets.models import Target  # noqa: F401
from app.modules.activity_logs.models import ActivityLog  # noqa: F401
from app.modules.attendance.models import Attendance  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.chat.models import ChatRoom, ChatMessage, ChatRead  # noqa: F401

# ---- Import routers ----
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.clients.router import router as clients_router
from app.modules.requirements.router import router as requirements_router
from app.modules.resumes.router import router as resumes_router
from app.modules.applications.router import router as applications_router, ai_router
from app.modules.targets.router import router as targets_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.reports.router import router as reports_router
from app.modules.attendance.router import router as attendance_router
from app.modules.notifications.router import router as notifications_router
from app.modules.activity_logs.router import router as activity_logs_router
from app.modules.chat.router import router as chat_router
from app.modules.chat.websocket import router as chat_ws_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    print("🚀 Apply Flow Careers API starting...")
    # Auto-create new tables and migrate missing columns
    import sqlalchemy
    from app.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate applications table columns if missing
        for col, col_type in [
            ("current_round", "VARCHAR(100)"),
            ("interview_date", "TIMESTAMP"),
            ("confidence", "INTEGER DEFAULT 95"),
            ("last_email_snippet", "TEXT"),
            ("is_ai_processed", "BOOLEAN DEFAULT 0"),
            ("updated_at", "TIMESTAMP"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE applications ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate clients table columns
        for col, col_type in [
            ("deactivated_at", "TIMESTAMP"),
            ("archived_at", "TIMESTAMP"),
            ("status", "VARCHAR(20) DEFAULT 'active'"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE clients ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate users table columns
        for col, col_type in [
            ("status", "VARCHAR(20) DEFAULT 'active'"),
            ("phone", "VARCHAR(50)"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate requirements table columns
        for col, col_type in [
            ("job_title", "VARCHAR(200)"),
            ("job_url", "VARCHAR(500)"),
            ("priority", "VARCHAR(20) DEFAULT 'Medium'"),
            ("notes", "TEXT"),
            ("created_by", "CHAR(32)"),
            ("completed_by", "CHAR(32)"),
            ("completed_at", "TIMESTAMP"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE requirements ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate chat_rooms table columns
        for col, col_type in [
            ("status", "VARCHAR(20) DEFAULT 'active'"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE chat_rooms ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate targets table columns
        for col, col_type in [
            ("status", "VARCHAR(20) DEFAULT 'active'"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE targets ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate employee_clients table columns
        for col, col_type in [
            ("is_primary", "BOOLEAN DEFAULT 0"),
            ("active", "BOOLEAN DEFAULT 1"),
            ("assigned_at", "TIMESTAMP"),
            ("assigned_by", "CHAR(32)"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE employee_clients ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate chat_reads table columns
        for col, col_type in [
            ("last_read_at", "TIMESTAMP"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE chat_reads ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        # Migrate applications table columns for Smart Resume Linking
        for col, col_type in [
            ("candidate_name", "VARCHAR(200)"),
            ("company", "VARCHAR(100)"),
            ("role", "VARCHAR(200)"),
        ]:
            try:
                await conn.execute(sqlalchemy.text(f"ALTER TABLE applications ADD COLUMN {col} {col_type}"))
            except Exception:
                pass

        try:
            res = await conn.execute(sqlalchemy.text("PRAGMA table_info(applications)"))
            cols = res.fetchall()
            resume_col = [c for c in cols if c[1] == 'resume_id']
            if resume_col and resume_col[0][3] == 1:
                await conn.execute(sqlalchemy.text("PRAGMA foreign_keys=OFF"))
                await conn.execute(sqlalchemy.text("""
                    CREATE TABLE applications_new (
                        id CHAR(32) PRIMARY KEY,
                        resume_id CHAR(32),
                        requirement_id CHAR(32),
                        employee_id CHAR(32) NOT NULL,
                        client_id CHAR(32),
                        status VARCHAR(50) NOT NULL DEFAULT 'Submitted',
                        applied_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        current_round VARCHAR(100),
                        interview_date TIMESTAMP,
                        confidence INTEGER DEFAULT 95,
                        last_email_snippet TEXT,
                        is_ai_processed BOOLEAN DEFAULT 0,
                        updated_at TIMESTAMP,
                        candidate_name VARCHAR(200),
                        company VARCHAR(100),
                        role VARCHAR(200),
                        FOREIGN KEY(resume_id) REFERENCES resumes (id),
                        FOREIGN KEY(requirement_id) REFERENCES requirements (id),
                        FOREIGN KEY(employee_id) REFERENCES users (id),
                        FOREIGN KEY(client_id) REFERENCES clients (id)
                    )
                """))
                await conn.execute(sqlalchemy.text("""
                    INSERT INTO applications_new (id, resume_id, requirement_id, employee_id, client_id, status, applied_date, current_round, interview_date, confidence, last_email_snippet, is_ai_processed, updated_at, candidate_name, company, role)
                    SELECT id, resume_id, requirement_id, employee_id, client_id, status, applied_date, current_round, interview_date, confidence, last_email_snippet, is_ai_processed, updated_at, candidate_name, company, role FROM applications
                """))
                await conn.execute(sqlalchemy.text("DROP TABLE applications"))
                await conn.execute(sqlalchemy.text("ALTER TABLE applications_new RENAME TO applications"))
                await conn.execute(sqlalchemy.text("PRAGMA foreign_keys=ON"))
        except Exception:
            pass
    print("✅ Database tables and columns verified.")
    yield
    print("👋 Apply Flow Careers API shutting down...")


app = FastAPI(
    title="Apply Flow Careers API",
    description="Internal recruitment agency platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,  # Required for HTTP-only cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Register routers ----
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(clients_router)
app.include_router(requirements_router)
app.include_router(resumes_router)
app.include_router(applications_router)
app.include_router(ai_router)
app.include_router(targets_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(attendance_router)
app.include_router(notifications_router)
app.include_router(activity_logs_router)
app.include_router(chat_router)
app.include_router(chat_ws_router)




@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Apply Flow Careers API"}
