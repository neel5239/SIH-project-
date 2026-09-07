from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "004_summary"
down_revision = "003_documents"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "summaries",
        sa.Column("summary_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_summaries_session_id", "summaries", ["session_id"])

    op.create_table(
        "provenance",
        sa.Column("prov_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("audio", JSONB),
        sa.Column("image", JSONB),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_provenance_session_id", "provenance", ["session_id"])

    op.create_table(
        "corrections",
        sa.Column("correction_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("summary_id", UUID(as_uuid=True)),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("field_path", sa.Text(), nullable=False),
        sa.Column("generated_value", sa.Text()),
        sa.Column("corrected_value", sa.Text(), nullable=False),
        sa.Column("source_module", sa.Text()),
        sa.Column("source_prov_id", UUID(as_uuid=True)),
        sa.Column("corrected_by", sa.Text(), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "guardian_log",
        sa.Column("log_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True)),
        sa.Column("summary_id", UUID(as_uuid=True)),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("rewritten_text", sa.Text()),
        sa.Column("guardian_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prakriti_scores",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("vata", sa.Float(), nullable=False),
        sa.Column("pitta", sa.Float(), nullable=False),
        sa.Column("kapha", sa.Float(), nullable=False),
        sa.Column("dominant", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("items_answered", sa.Integer(), nullable=False),
        sa.Column("items_total", sa.Integer(), nullable=False),
        sa.Column("namaste_code", sa.Text()),
        sa.Column("icd11_tm2_code", sa.Text()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("prakriti_scores")
    op.drop_table("guardian_log")
    op.drop_table("corrections")
    op.drop_table("provenance")
    op.drop_table("summaries")
