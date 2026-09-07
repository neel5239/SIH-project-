from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005_platform"
down_revision = "004_summary"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "triage_queue",
        sa.Column("entry_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_number", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("reason", sa.Text()),
        sa.Column("rule_id", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_by", sa.Text()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_triage_queue_status_priority", "triage_queue", ["status", "priority"])

    op.create_table(
        "jobs",
        sa.Column("job_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True)),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "fhir_outbox",
        sa.Column("outbox_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True)),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "metrics_rollup",
        sa.Column("metric_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("labels", JSONB, nullable=False),
        sa.Column("bucket_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("metrics_rollup")
    op.drop_table("fhir_outbox")
    op.drop_table("jobs")
    op.drop_table("triage_queue")
