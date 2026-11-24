"""Add idempotent offline draft sync and listing image metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0004_listing_images_sync"
down_revision = "0003_audit_inquiries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("client_sync_id", sa.String(36), nullable=True))
    op.create_index("ix_listings_client_sync_id", "listings", ["client_sync_id"], unique=True)
    op.create_table(
        "listing_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "listing_id", sa.String(36),
            sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("client_image_id", sa.String(36), nullable=False, unique=True),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(80), nullable=False, server_default="image/jpeg"),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_listing_images_listing_id", "listing_images", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_listing_images_listing_id", table_name="listing_images")
    op.drop_table("listing_images")
    op.drop_index("ix_listings_client_sync_id", table_name="listings")
    op.drop_column("listings", "client_sync_id")
