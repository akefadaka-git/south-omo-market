"""Add versioned seller listing edits and moderation.

Revision ID: 0021_listing_edit_versions
Revises: 0020_seller_contact_consent
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_listing_edit_versions"
down_revision = "0020_seller_contact_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_edits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("listing_id", sa.String(length=36), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("proposed_values", sa.JSON(), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending_review"),
        sa.Column("pending_key", sa.String(length=16), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("listing_id", "pending_key", name="uq_listing_edit_one_pending"),
        sa.CheckConstraint("status IN ('pending_review', 'approved', 'rejected')", name="ck_listing_edit_status"),
    )
    op.create_index("ix_listing_edits_listing_id", "listing_edits", ["listing_id"])
    op.create_index("ix_listing_edits_status", "listing_edits", ["status"])


def downgrade() -> None:
    op.drop_index("ix_listing_edits_status", table_name="listing_edits")
    op.drop_index("ix_listing_edits_listing_id", table_name="listing_edits")
    op.drop_table("listing_edits")
