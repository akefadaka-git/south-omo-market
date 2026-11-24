"""Add business-scoped commerce catalog and inventory.

Revision ID: 0014_commerce_catalog_inventory
Revises: 0013_governance_hardening
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_commerce_catalog_inventory"
down_revision = "0013_governance_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commerce_catalog_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("listing_id", sa.String(36), sa.ForeignKey("listings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False, server_default="item"),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("business_id", "sku", name="uq_commerce_catalog_business_sku"),
        sa.CheckConstraint("unit_price_minor >= 0", name="ck_commerce_catalog_price_nonnegative"),
        sa.CheckConstraint("status IN ('draft','active','paused','archived')", name="ck_commerce_catalog_status"),
        sa.CheckConstraint("currency = 'ETB'", name="ck_commerce_catalog_currency_v1"),
    )
    op.create_index("ix_commerce_catalog_business_status", "commerce_catalog_items", ["business_id", "status"])
    op.create_index("ix_commerce_catalog_category", "commerce_catalog_items", ["category_id"])

    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.String(36), sa.ForeignKey("commerce_catalog_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_on_hand", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("catalog_item_id", name="uq_inventory_balance_catalog_item"),
        sa.CheckConstraint("quantity_on_hand >= 0 AND quantity_reserved >= 0", name="ck_inventory_quantities_nonnegative"),
        sa.CheckConstraint("quantity_reserved <= quantity_on_hand", name="ck_inventory_reserved_lte_on_hand"),
    )
    op.create_index("ix_inventory_balances_business", "inventory_balances", ["business_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.String(36), sa.ForeignKey("commerce_catalog_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("movement_type", sa.String(24), nullable=False),
        sa.Column("quantity_delta", sa.BigInteger(), nullable=False),
        sa.Column("reference_type", sa.String(40), nullable=True),
        sa.Column("reference_id", sa.String(36), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("business_id", "idempotency_key", name="uq_inventory_movement_idempotency"),
        sa.CheckConstraint("movement_type IN ('receipt','adjustment','reservation','release','fulfillment')", name="ck_inventory_movement_type"),
        sa.CheckConstraint("quantity_delta <> 0", name="ck_inventory_movement_nonzero"),
    )
    op.create_index("ix_inventory_movements_item_created", "inventory_movements", ["catalog_item_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_inventory_movements_item_created", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_balances_business", table_name="inventory_balances")
    op.drop_table("inventory_balances")
    op.drop_index("ix_commerce_catalog_category", table_name="commerce_catalog_items")
    op.drop_index("ix_commerce_catalog_business_status", table_name="commerce_catalog_items")
    op.drop_table("commerce_catalog_items")
