from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "002_conversation"
down_revision = "001_core"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "slots",
        sa.Column("slot_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("ontology_key", sa.String(255), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("unit", sa.String(32)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("framework", sa.String(32), nullable=False),
        sa.Column("section", sa.String(64), nullable=False),
        sa.Column("answered_by", sa.String(16), nullable=False),
        sa.Column("input_mode", sa.String(16), nullable=False),
        sa.Column("provenance_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_slots_session_id", "slots", ["session_id"])

    op.create_table(
        "interview_state",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("active_branch", sa.Text()),
        sa.Column("asked_keys", ARRAY(sa.Text())),
        sa.Column("skipped_keys", ARRAY(sa.Text())),
        sa.Column("section_coverage", JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("last_turn_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("end_reason", sa.Text()),
    )

    op.create_table(
        "red_flag_events",
        sa.Column("event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("triggering_slots", ARRAY(UUID(as_uuid=True))),
        sa.Column("detector", sa.Text(), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_by", sa.Text()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_red_flag_session_id", "red_flag_events", ["session_id"])

def downgrade():
    op.drop_table("red_flag_events")
    op.drop_table("interview_state")
    op.drop_table("slots")
