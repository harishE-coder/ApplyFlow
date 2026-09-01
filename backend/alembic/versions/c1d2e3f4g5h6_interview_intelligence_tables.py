"""interview_intelligence_tables

Revision ID: c1d2e3f4g5h6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-01 14:50:00.000000

Adds tables for Interview Intelligence Pipeline:
- email_training_data: Metadata, message_id, in_reply_to, storage keys, pipeline_version, needs_retraining, and status
- interview_events: Application timeline interview events with event_sequence and deadline
- model_versions: Model version registry, accuracy, and storage references
- teacher_disagreements: High-value active learning disagreement dataset for model retraining
- review_actions: Audit trail for human review relabeling and verification actions
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4g5h6'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create email_training_data table
    op.create_table(
        'email_training_data',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('thread_id', sa.UUID(), nullable=True),
        sa.Column('message_id', sa.String(length=500), nullable=True),
        sa.Column('in_reply_to', sa.String(length=500), nullable=True),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('sender_email', sa.String(length=320), nullable=True),
        sa.Column('sender_domain', sa.String(length=255), nullable=True),
        sa.Column('sender_name', sa.String(length=255), nullable=True),
        sa.Column('body_preview', sa.String(length=300), nullable=True),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('raw_storage_key', sa.String(length=500), nullable=True),
        sa.Column('body_sha256', sa.String(length=64), nullable=False),
        sa.Column('attachment_metadata', sa.JSON(), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='local'),
        sa.Column('classification_source_version', sa.String(length=100), nullable=True),
        sa.Column('pipeline_version', sa.String(length=50), nullable=False, server_default='interview_pipeline_v2.0'),
        sa.Column('needs_retraining', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('processing_status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_email_training_data_email_hash', 'email_training_data', ['email_hash'], unique=False)
    op.create_index('ix_email_training_data_message_id', 'email_training_data', ['message_id'], unique=False)
    op.create_index('ix_email_training_data_in_reply_to', 'email_training_data', ['in_reply_to'], unique=False)
    op.create_index('ix_email_training_data_sender_email', 'email_training_data', ['sender_email'], unique=False)
    op.create_index('ix_email_training_data_sender_domain', 'email_training_data', ['sender_domain'], unique=False)
    op.create_index('ix_email_training_data_storage_key', 'email_training_data', ['storage_key'], unique=False)
    op.create_index('ix_email_training_data_category', 'email_training_data', ['category'], unique=False)
    op.create_index('ix_email_training_data_processing_status', 'email_training_data', ['processing_status'], unique=False)
    op.create_index('ix_email_training_data_created_at', 'email_training_data', ['created_at'], unique=False)
    op.create_index('ix_email_train_company_cat', 'email_training_data', ['company', 'category'], unique=False)
    op.create_index('ix_email_train_created_cat', 'email_training_data', ['created_at', 'category'], unique=False)
    op.create_index('ix_email_train_domain_cat', 'email_training_data', ['sender_domain', 'category'], unique=False)
    op.create_index('ix_email_train_company_created', 'email_training_data', ['company', 'created_at'], unique=False)
    op.create_index('ix_email_train_status_created', 'email_training_data', ['processing_status', 'created_at'], unique=False)
    op.create_index('ix_email_train_retraining', 'email_training_data', ['needs_retraining', 'created_at'], unique=False)

    # 2. Create interview_events table
    op.create_table(
        'interview_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('thread_id', sa.UUID(), nullable=True),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('email_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('round_name', sa.String(length=255), nullable=True),
        sa.Column('round_type', sa.String(length=100), nullable=True),
        sa.Column('round', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Scheduled'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meeting_link', sa.String(length=1000), nullable=True),
        sa.Column('deadline', sa.String(length=255), nullable=True),
        sa.Column('recruiter', sa.String(length=255), nullable=True),
        sa.Column('raw_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['email_id'], ['email_training_data.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interview_events_thread_id', 'interview_events', ['thread_id'], unique=False)
    op.create_index('ix_interview_events_thread_seq', 'interview_events', ['thread_id', 'event_sequence'], unique=False)
    op.create_index('ix_interview_events_application_id', 'interview_events', ['application_id'], unique=False)
    op.create_index('ix_interview_events_email_id', 'interview_events', ['email_id'], unique=False)
    op.create_index('ix_interview_events_created_at', 'interview_events', ['created_at'], unique=False)
    op.create_index('ix_interview_events_status_sched', 'interview_events', ['status', 'scheduled_at'], unique=False)

    # 3. Create model_versions table
    op.create_table(
        'model_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('samples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_type', sa.String(length=20), nullable=False, server_default='supabase'),
        sa.Column('trained_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('model_path', sa.String(length=500), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )
    op.create_index('ix_model_versions_version', 'model_versions', ['version'], unique=True)
    op.create_index('ix_model_versions_active', 'model_versions', ['active'], unique=False)
    op.create_index('ix_model_versions_active_trained', 'model_versions', ['active', 'trained_at'], unique=False)

    # 4. Create teacher_disagreements table
    op.create_table(
        'teacher_disagreements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_id', sa.UUID(), nullable=False),
        sa.Column('local_label', sa.String(length=100), nullable=True),
        sa.Column('local_confidence', sa.Integer(), nullable=True),
        sa.Column('ai_label', sa.String(length=100), nullable=True),
        sa.Column('ai_confidence', sa.Integer(), nullable=True),
        sa.Column('human_label', sa.String(length=100), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['email_id'], ['email_training_data.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_teacher_disagreements_email_id', 'teacher_disagreements', ['email_id'], unique=False)
    op.create_index('ix_teacher_disagreements_resolved', 'teacher_disagreements', ['resolved'], unique=False)
    op.create_index('ix_disagreements_resolved_created', 'teacher_disagreements', ['resolved', 'created_at'], unique=False)

    # 5. Create review_actions table
    op.create_table(
        'review_actions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_id', sa.UUID(), nullable=False),
        sa.Column('reviewer', sa.String(length=255), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=True),
        sa.Column('old_label', sa.String(length=100), nullable=True),
        sa.Column('new_label', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['email_id'], ['email_training_data.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_actions_email_id', 'review_actions', ['email_id'], unique=False)
    op.create_index('ix_review_actions_reviewer_id', 'review_actions', ['reviewer_id'], unique=False)
    op.create_index('ix_review_actions_created_at', 'review_actions', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop review_actions
    op.drop_index('ix_review_actions_created_at', table_name='review_actions')
    op.drop_index('ix_review_actions_reviewer_id', table_name='review_actions')
    op.drop_index('ix_review_actions_email_id', table_name='review_actions')
    op.drop_table('review_actions')

    # Drop teacher_disagreements
    op.drop_index('ix_disagreements_resolved_created', table_name='teacher_disagreements')
    op.drop_index('ix_teacher_disagreements_resolved', table_name='teacher_disagreements')
    op.drop_index('ix_teacher_disagreements_email_id', table_name='teacher_disagreements')
    op.drop_table('teacher_disagreements')

    # Drop model_versions
    op.drop_index('ix_model_versions_active_trained', table_name='model_versions')
    op.drop_index('ix_model_versions_active', table_name='model_versions')
    op.drop_index('ix_model_versions_version', table_name='model_versions')
    op.drop_table('model_versions')

    # Drop interview_events
    op.drop_index('ix_interview_events_status_sched', table_name='interview_events')
    op.drop_index('ix_interview_events_created_at', table_name='interview_events')
    op.drop_index('ix_interview_events_email_id', table_name='interview_events')
    op.drop_index('ix_interview_events_application_id', table_name='interview_events')
    op.drop_table('interview_events')

    # Drop email_training_data
    op.drop_index('ix_email_train_retraining', table_name='email_training_data')
    op.drop_index('ix_email_train_status_created', table_name='email_training_data')
    op.drop_index('ix_email_train_company_created', table_name='email_training_data')
    op.drop_index('ix_email_train_domain_cat', table_name='email_training_data')
    op.drop_index('ix_email_train_created_cat', table_name='email_training_data')
    op.drop_index('ix_email_train_company_cat', table_name='email_training_data')
    op.drop_index('ix_email_training_data_created_at', table_name='email_training_data')
    op.drop_index('ix_email_training_data_processing_status', table_name='email_training_data')
    op.drop_index('ix_email_training_data_category', table_name='email_training_data')
    op.drop_index('ix_email_training_data_storage_key', table_name='email_training_data')
    op.drop_index('ix_email_training_data_sender_domain', table_name='email_training_data')
    op.drop_index('ix_email_training_data_sender_email', table_name='email_training_data')
    op.drop_index('ix_email_training_data_in_reply_to', table_name='email_training_data')
    op.drop_index('ix_email_training_data_message_id', table_name='email_training_data')
    op.drop_index('ix_email_training_data_email_hash', table_name='email_training_data')
    op.drop_table('email_training_data')
