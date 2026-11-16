"""Initial marketplace schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("phone_number", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_table("seller_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("public_name", sa.String(160), nullable=False),
        sa.Column("location_label", sa.String(160), nullable=False))
    op.create_index("ix_seller_profiles_user_id", "seller_profiles", ["user_id"], unique=True)
    op.create_table("categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_table("listings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("seller_id", sa.String(36), sa.ForeignKey("seller_profiles.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("location_label", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_listings_seller_id", "listings", ["seller_id"])
    op.create_index("ix_listings_category_id", "listings", ["category_id"])
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_table("inquiries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("listing_id", sa.String(36), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("buyer_name", sa.String(120), nullable=False),
        sa.Column("contact_value", sa.String(160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_inquiries_listing_id", "inquiries", ["listing_id"])

def downgrade() -> None:
    op.drop_index("ix_inquiries_listing_id", table_name="inquiries")
    op.drop_table("inquiries")
    op.drop_index("ix_listings_status", table_name="listings")
    op.drop_index("ix_listings_category_id", table_name="listings")
    op.drop_index("ix_listings_seller_id", table_name="listings")
    op.drop_table("listings")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_seller_profiles_user_id", table_name="seller_profiles")
    op.drop_table("seller_profiles")
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_table("users")
