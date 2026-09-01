"""fix_delete_blockers

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-09-01 17:45:00.000000

Targeted migration for foreign key delete blockers:
- chat_rooms.client_id -> CASCADE
- chat_messages.room_id -> CASCADE
- chat_messages.sender_id -> SET NULL (nullable)
- chat_reads.user_id -> CASCADE, chat_reads.room_id -> CASCADE, last_read_message_id -> SET NULL
- attendance.employee_id -> CASCADE
- notifications.user_id -> CASCADE
- activity_logs.user_id -> SET NULL (nullable)
- employee_clients.client_id -> CASCADE, employee_id -> CASCADE
- requirements.client_id -> RESTRICT, assigned_employee_id -> SET NULL
- applications.resume_id -> CASCADE, client_id -> SET NULL, employee_id -> SET NULL
- resumes.client_id -> SET NULL (nullable), uploaded_by -> SET NULL (nullable)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2e3f4g5h6i7'
down_revision: str | None = 'c1d2e3f4g5h6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        # 1. Nullable column alterations for SET NULL targets
        op.alter_column('chat_messages', 'sender_id', existing_type=sa.UUID(), nullable=True)
        op.alter_column('activity_logs', 'user_id', existing_type=sa.UUID(), nullable=True)
        op.alter_column('resumes', 'client_id', existing_type=sa.UUID(), nullable=True)
        op.alter_column('resumes', 'uploaded_by', existing_type=sa.UUID(), nullable=True)
        op.alter_column('applications', 'employee_id', existing_type=sa.UUID(), nullable=True)
        op.alter_column('applications', 'client_id', existing_type=sa.UUID(), nullable=True)
        op.alter_column('email_intake', 'uploaded_by', existing_type=sa.UUID(), nullable=True)
        op.alter_column('email_intake', 'client_id', existing_type=sa.UUID(), nullable=True)

        # 2. Update Foreign Key constraints on PostgreSQL
        # Chat Room & Messages
        op.drop_constraint('chat_rooms_client_id_fkey', 'chat_rooms', type_='foreignkey')
        op.create_foreign_key('chat_rooms_client_id_fkey', 'chat_rooms', 'clients', ['client_id'], ['id'], ondelete='CASCADE')

        op.drop_constraint('chat_messages_room_id_fkey', 'chat_messages', type_='foreignkey')
        op.drop_constraint('chat_messages_sender_id_fkey', 'chat_messages', type_='foreignkey')
        op.create_foreign_key('chat_messages_room_id_fkey', 'chat_messages', 'chat_rooms', ['room_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('chat_messages_sender_id_fkey', 'chat_messages', 'users', ['sender_id'], ['id'], ondelete='SET NULL')

        op.drop_constraint('chat_reads_user_id_fkey', 'chat_reads', type_='foreignkey')
        op.drop_constraint('chat_reads_room_id_fkey', 'chat_reads', type_='foreignkey')
        op.drop_constraint('chat_reads_last_read_message_id_fkey', 'chat_reads', type_='foreignkey')
        op.create_foreign_key('chat_reads_user_id_fkey', 'chat_reads', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('chat_reads_room_id_fkey', 'chat_reads', 'chat_rooms', ['room_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('chat_reads_last_read_message_id_fkey', 'chat_reads', 'chat_messages', ['last_read_message_id'], ['id'], ondelete='SET NULL')

        # Users, Attendance, Notifications, Activity Logs
        op.drop_constraint('attendance_employee_id_fkey', 'attendance', type_='foreignkey')
        op.create_foreign_key('attendance_employee_id_fkey', 'attendance', 'users', ['employee_id'], ['id'], ondelete='CASCADE')

        op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
        op.create_foreign_key('notifications_user_id_fkey', 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')

        op.drop_constraint('activity_logs_user_id_fkey', 'activity_logs', type_='foreignkey')
        op.create_foreign_key('activity_logs_user_id_fkey', 'activity_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')

        # Employee Clients & SubAdmin Assignments
        op.drop_constraint('employee_clients_client_id_fkey', 'employee_clients', type_='foreignkey')
        op.drop_constraint('employee_clients_employee_id_fkey', 'employee_clients', type_='foreignkey')
        op.create_foreign_key('employee_clients_client_id_fkey', 'employee_clients', 'clients', ['client_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('employee_clients_employee_id_fkey', 'employee_clients', 'users', ['employee_id'], ['id'], ondelete='CASCADE')

        op.drop_constraint('sub_admin_assignments_sub_admin_id_fkey', 'sub_admin_assignments', type_='foreignkey')
        op.drop_constraint('sub_admin_assignments_employee_id_fkey', 'sub_admin_assignments', type_='foreignkey')
        op.drop_constraint('sub_admin_assignments_client_id_fkey', 'sub_admin_assignments', type_='foreignkey')
        op.create_foreign_key('sub_admin_assignments_sub_admin_id_fkey', 'sub_admin_assignments', 'users', ['sub_admin_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('sub_admin_assignments_employee_id_fkey', 'sub_admin_assignments', 'users', ['employee_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('sub_admin_assignments_client_id_fkey', 'sub_admin_assignments', 'clients', ['client_id'], ['id'], ondelete='CASCADE')

        # Targets & Requirements
        op.drop_constraint('targets_client_id_fkey', 'targets', type_='foreignkey')
        op.drop_constraint('targets_employee_id_fkey', 'targets', type_='foreignkey')
        op.create_foreign_key('targets_client_id_fkey', 'targets', 'clients', ['client_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('targets_employee_id_fkey', 'targets', 'users', ['employee_id'], ['id'], ondelete='CASCADE')

        op.drop_constraint('requirements_client_id_fkey', 'requirements', type_='foreignkey')
        op.drop_constraint('requirements_assigned_employee_id_fkey', 'requirements', type_='foreignkey')
        op.create_foreign_key('requirements_client_id_fkey', 'requirements', 'clients', ['client_id'], ['id'], ondelete='RESTRICT')
        op.create_foreign_key('requirements_assigned_employee_id_fkey', 'requirements', 'users', ['assigned_employee_id'], ['id'], ondelete='SET NULL')

        # Resumes, Applications & Timeline
        op.drop_constraint('resumes_client_id_fkey', 'resumes', type_='foreignkey')
        op.drop_constraint('resumes_uploaded_by_fkey', 'resumes', type_='foreignkey')
        op.drop_constraint('resumes_requirement_id_fkey', 'resumes', type_='foreignkey')
        op.create_foreign_key('resumes_client_id_fkey', 'resumes', 'clients', ['client_id'], ['id'], ondelete='SET NULL')
        op.create_foreign_key('resumes_uploaded_by_fkey', 'resumes', 'users', ['uploaded_by'], ['id'], ondelete='SET NULL')
        op.create_foreign_key('resumes_requirement_id_fkey', 'resumes', 'requirements', ['requirement_id'], ['id'], ondelete='SET NULL')

        op.drop_constraint('applications_resume_id_fkey', 'applications', type_='foreignkey')
        op.drop_constraint('applications_client_id_fkey', 'applications', type_='foreignkey')
        op.drop_constraint('applications_employee_id_fkey', 'applications', type_='foreignkey')
        op.drop_constraint('applications_requirement_id_fkey', 'applications', type_='foreignkey')
        op.create_foreign_key('applications_resume_id_fkey', 'applications', 'resumes', ['resume_id'], ['id'], ondelete='CASCADE')
        op.create_foreign_key('applications_client_id_fkey', 'applications', 'clients', ['client_id'], ['id'], ondelete='SET NULL')
        op.create_foreign_key('applications_employee_id_fkey', 'applications', 'users', ['employee_id'], ['id'], ondelete='SET NULL')
        op.create_foreign_key('applications_requirement_id_fkey', 'applications', 'requirements', ['requirement_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    pass
