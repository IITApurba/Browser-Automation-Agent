"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

run_status = postgresql.ENUM(
    "pending", "running", "paused_captcha", "paused_error", "completed", "failed", name="run_status"
)
step_status = postgresql.ENUM("pending", "running", "ok", "error", name="step_status")
checkpoint_reason = postgresql.ENUM("captcha", "error", "manual", name="checkpoint_reason")


def upgrade() -> None:
    bind = op.get_bind()
    run_status.create(bind, checkfirst=True)
    step_status.create(bind, checkfirst=True)
    checkpoint_reason.create(bind, checkfirst=True)

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("extraction_schema", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("status", run_status, nullable=False, server_default="pending"),
        sa.Column("plan", postgresql.JSONB(), nullable=True),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("input", postgresql.JSONB(), nullable=True),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("status", step_status, nullable=False, server_default="pending"),
        sa.Column("dom_fingerprint", sa.String(), nullable=True),
        sa.Column("screenshot_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("steps.id"), nullable=True),
        sa.Column("reason", checkpoint_reason, nullable=False),
        sa.Column("page_url", sa.String(), nullable=False),
        sa.Column("storage_state", postgresql.JSONB(), nullable=True),
        sa.Column("extracted_so_far", postgresql.JSONB(), nullable=True),
        sa.Column("scratchpad_memory", postgresql.JSONB(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "extracted_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("steps.id"), nullable=True),
        sa.Column("schema_name", sa.String(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_domain", sa.String(), nullable=False),
        sa.Column("username_ref", sa.String(), nullable=False),
        sa.Column("auth_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("storage_state", postgresql.JSONB(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "memory_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("memory_entries")
    op.drop_table("sessions")
    op.drop_table("credentials")
    op.drop_table("extracted_data")
    op.drop_table("checkpoints")
    op.drop_table("steps")
    op.drop_table("runs")
    op.drop_table("reports")
    op.drop_table("tasks")

    bind = op.get_bind()
    checkpoint_reason.drop(bind, checkfirst=True)
    step_status.drop(bind, checkfirst=True)
    run_status.drop(bind, checkfirst=True)
