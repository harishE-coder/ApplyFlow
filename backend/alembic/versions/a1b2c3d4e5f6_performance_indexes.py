"""performance_indexes

Revision ID: a1b2c3d4e5f6
Revises: 84e0aa572138
Create Date: 2026-08-27 06:40:00.000000

Safe composite and single-column performance indexes across core tables.
Reversible on both SQLite and PostgreSQL.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '84e0aa572138'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_resumes_client_date ON resumes (client_id, resume_date)",
        "CREATE INDEX IF NOT EXISTS ix_resumes_uploader_date ON resumes (uploaded_by, resume_date)",
        "CREATE INDEX IF NOT EXISTS ix_resumes_client_comp ON resumes (client_id, company)",
        "CREATE INDEX IF NOT EXISTS ix_resumes_tag ON resumes (resume_id_tag)",
        "CREATE INDEX IF NOT EXISTS ix_resumes_role ON resumes (role)",
        "CREATE INDEX IF NOT EXISTS ix_apps_emp_applied ON applications (employee_id, applied_date)",
        "CREATE INDEX IF NOT EXISTS ix_apps_status_applied ON applications (status, applied_date)",
        "CREATE INDEX IF NOT EXISTS ix_apps_req_id ON applications (requirement_id)",
        "CREATE INDEX IF NOT EXISTS ix_targets_emp_status ON targets (employee_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_targets_client_status ON targets (client_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_targets_effective_date ON targets (effective_date)",
        "CREATE INDEX IF NOT EXISTS ix_attendance_emp_date ON attendance (employee_id, work_date)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_read_created ON notifications (user_id, is_read, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_chat_messages_room_created ON chat_messages (room_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_emp_client_active ON employee_clients (client_id, active)",
        "CREATE INDEX IF NOT EXISTS ix_emp_client_emp_active ON employee_clients (employee_id, active)",
        "CREATE INDEX IF NOT EXISTS ix_users_role_active ON users (role, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_users_email_active ON users (email, is_active)",
    ]
    for idx_sql in indexes:
        op.execute(sa.text(idx_sql))


def downgrade() -> None:
    indexes = [
        "DROP INDEX IF EXISTS ix_resumes_client_date",
        "DROP INDEX IF EXISTS ix_resumes_uploader_date",
        "DROP INDEX IF EXISTS ix_resumes_client_comp",
        "DROP INDEX IF EXISTS ix_resumes_tag",
        "DROP INDEX IF EXISTS ix_resumes_role",
        "DROP INDEX IF EXISTS ix_apps_emp_applied",
        "DROP INDEX IF EXISTS ix_apps_status_applied",
        "DROP INDEX IF EXISTS ix_apps_req_id",
        "DROP INDEX IF EXISTS ix_targets_emp_status",
        "DROP INDEX IF EXISTS ix_targets_client_status",
        "DROP INDEX IF EXISTS ix_targets_effective_date",
        "DROP INDEX IF EXISTS ix_attendance_emp_date",
        "DROP INDEX IF EXISTS ix_notifications_user_read_created",
        "DROP INDEX IF EXISTS ix_chat_messages_room_created",
        "DROP INDEX IF EXISTS ix_emp_client_active",
        "DROP INDEX IF EXISTS ix_emp_client_emp_active",
        "DROP INDEX IF EXISTS ix_users_role_active",
        "DROP INDEX IF EXISTS ix_users_email_active",
    ]
    for drop_sql in indexes:
        op.execute(sa.text(drop_sql))
