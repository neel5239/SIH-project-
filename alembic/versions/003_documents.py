from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003_documents"
down_revision = "002_conversation"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "documents",
        sa.Column("document_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(64)),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_documents_session_id", "documents", ["session_id"])

    op.create_table(
        "doc_entities",
        sa.Column("entity_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_verification", sa.Boolean(), nullable=False),
        sa.Column("source", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_doc_entities_session_id", "doc_entities", ["session_id"])

    op.create_table(
        "ocr_training_pairs",
        sa.Column("pair_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True)),
        sa.Column("entity_id", UUID(as_uuid=True)),
        sa.Column("input_object_key", sa.Text()),
        sa.Column("corrected_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("ocr_training_pairs")
    op.drop_table("doc_entities")
    op.drop_table("documents")
