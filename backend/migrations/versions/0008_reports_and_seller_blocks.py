"""Add user suspension and marketplace reports with review lifecycle."""
from alembic import op
import sqlalchemy as sa

revision = "0008_reports_and_seller_blocks"
down_revision = "0007_catalogue_expansion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reporter_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("listing_id", sa.String(36), sa.ForeignKey("listings.id"), nullable=True),
        sa.Column("seller_id", sa.String(36), sa.ForeignKey("seller_profiles.id"), nullable=True),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    with op.batch_alter_table("reports") as batch:
        batch.create_check_constraint(
            "ck_reports_exactly_one_target",
            "(listing_id IS NOT NULL AND seller_id IS NULL) OR (listing_id IS NULL AND seller_id IS NOT NULL)",
        )
    op.create_index("ix_reports_reporter_user_id", "reports", ["reporter_user_id"])
    op.create_index("ix_reports_listing_id", "reports", ["listing_id"])
    op.create_index("ix_reports_seller_id", "reports", ["seller_id"])
    op.create_index("ix_reports_status_created", "reports", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_status_created", table_name="reports")
    op.drop_index("ix_reports_seller_id", table_name="reports")
    op.drop_index("ix_reports_listing_id", table_name="reports")
    op.drop_index("ix_reports_reporter_user_id", table_name="reports")
    with op.batch_alter_table("reports") as batch:
        batch.drop_constraint("ck_reports_exactly_one_target", type_="check")
    op.drop_table("reports")
    op.drop_column("users", "is_suspended")
