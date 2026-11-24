"""Add customer profile preferences and contact settings.

Revision ID: 0017_customer_profiles
Revises: 0016_commerce_cart_orders
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_customer_profiles"
down_revision = "0016_commerce_cart_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("preferred_location_id", sa.String(36), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("preferred_market_id", sa.String(36), sa.ForeignKey("markets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("preferred_language", sa.String(2), nullable=False, server_default="am"),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("profile_photo_key", sa.String(500), nullable=True),
        sa.Column("contact_preference", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_customer_profiles_user"),
        sa.CheckConstraint("preferred_language IN ('am','en')", name="ck_customer_profile_language"),
        sa.CheckConstraint("contact_preference IS NULL OR contact_preference IN ('phone','sms','email')", name="ck_customer_profile_contact_preference"),
    )
    op.create_index("ix_customer_profiles_user_id", "customer_profiles", ["user_id"])
    op.create_index("ix_customer_profiles_preferred_location_id", "customer_profiles", ["preferred_location_id"])
    op.create_index("ix_customer_profiles_preferred_market_id", "customer_profiles", ["preferred_market_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_profiles_preferred_market_id", table_name="customer_profiles")
    op.drop_index("ix_customer_profiles_preferred_location_id", table_name="customer_profiles")
    op.drop_index("ix_customer_profiles_user_id", table_name="customer_profiles")
    op.drop_table("customer_profiles")
