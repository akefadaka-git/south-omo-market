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
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $audit$
            BEGIN
                RAISE EXCEPTION 'audit_events are append-only';
            END;
            $audit$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER audit_events_append_only
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
        """)

    # Nullable for records created before buyer account linkage was introduced.
    with op.batch_alter_table("inquiries") as batch:
        batch.add_column(sa.Column(
            "buyer_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ))
        batch.add_column(sa.Column(
            "status", sa.String(16), nullable=False, server_default="open"
        ))
        batch.add_column(sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_inquiries_buyer_user_id", ["buyer_user_id"])
        batch.create_index("ix_inquiries_status", ["status"])


def downgrade() -> None:
    with op.batch_alter_table("inquiries") as batch:
        batch.drop_index("ix_inquiries_status")
        batch.drop_index("ix_inquiries_buyer_user_id")
        batch.drop_column("closed_at")
        batch.drop_column("read_at")
        batch.drop_column("status")
        batch.drop_column("buyer_user_id")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS reject_audit_event_mutation()")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_id", table_name="audit_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_table("audit_events")
