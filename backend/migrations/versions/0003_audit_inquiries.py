"""Add immutable audit events and seller inbox workflow fields."""
from alembic import op
import sqlalchemy as sa

revision = "0003_audit_inquiries"
down_revision = "0002_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # Nullable for records created before buyer account linkage was introduced.
    op.add_column("inquiries", sa.Column(
        "buyer_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    ))
    op.add_column("inquiries", sa.Column(
        "status", sa.String(16), nullable=False, server_default="open"
    ))
    op.add_column("inquiries", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("inquiries", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_inquiries_buyer_user_id", "inquiries", ["buyer_user_id"])
    op.create_index("ix_inquiries_status", "inquiries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_inquiries_status", table_name="inquiries")
    op.drop_index("ix_inquiries_buyer_user_id", table_name="inquiries")
    op.drop_column("inquiries", "closed_at")
    op.drop_column("inquiries", "read_at")
    op.drop_column("inquiries", "status")
    op.drop_column("inquiries", "buyer_user_id")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_table("audit_events")
