from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001_core"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "sessions",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("abha_id", sa.String(64)),
        sa.Column("patient_ref", UUID(as_uuid=True)),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("opd_type", sa.String(32), nullable=False),
        sa.Column("consent_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_number", sa.Integer(), nullable=False),
        sa.Column("kiosk_id", sa.String(128), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("phr_linked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_return_visit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("previous_encounter_id", UUID(as_uuid=True)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_abha_id", "sessions", ["abha_id"])
    op.create_index("ix_sessions_patient_ref", "sessions", ["patient_ref"])

    op.create_table(
        "patients",
        sa.Column("patient_ref", UUID(as_uuid=True), primary_key=True),
        sa.Column("abha_id", sa.String(64), unique=True),
        sa.Column("name_enc", sa.LargeBinary()),
        sa.Column("phone_enc", sa.LargeBinary()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "consents",
        sa.Column("consent_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("abha_id", sa.String(64)),
        sa.Column("consent_version", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("consent_text_hash", sa.String(128), nullable=False),
        sa.Column("permissions", JSONB, nullable=False),
        sa.Column("assent_method", sa.String(16), nullable=False),
        sa.Column("assent_audio_blob_id", UUID(as_uuid=True)),
        sa.Column("operator_present", sa.Boolean(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes", UUID(as_uuid=True)),
    )
    op.create_index("ix_consents_session_id", "consents", ["session_id"])

    op.create_table(
        "audit_log",
        sa.Column("event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_id", sa.String(128)),
        sa.Column("resource_id", sa.String(128)),
        sa.Column("session_id", UUID(as_uuid=True)),
        sa.Column("metadata_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_session_id", "audit_log", ["session_id"])

def downgrade():
    op.drop_table("audit_log")
    op.drop_table("consents")
    op.drop_table("patients")
    op.drop_table("sessions")
