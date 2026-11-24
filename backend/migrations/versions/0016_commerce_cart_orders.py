"""Add cart and order lifecycle without activating payment processing.

Revision ID: 0016_commerce_cart_orders
Revises: 0015_commerce_agreements
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_commerce_cart_orders"
down_revision = "0015_commerce_agreements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commerce_carts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("buyer_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("buyer_user_id", "business_id", "status", name="uq_commerce_cart_buyer_business_status"),
        sa.CheckConstraint("status IN ('active','converted','abandoned')", name="ck_commerce_cart_status"),
    )
    op.create_index("ix_commerce_carts_buyer", "commerce_carts", ["buyer_user_id", "status"])

    op.create_table(
        "commerce_cart_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cart_id", sa.String(36), sa.ForeignKey("commerce_carts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.String(36), sa.ForeignKey("commerce_catalog_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("cart_id", "catalog_item_id", name="uq_commerce_cart_item"),
        sa.CheckConstraint("quantity > 0", name="ck_commerce_cart_item_quantity"),
    )

    op.create_table(
        "commerce_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_number", sa.String(40), nullable=False, unique=True),
        sa.Column("buyer_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agreement_id", sa.String(36), sa.ForeignKey("commerce_agreements.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="placed"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("subtotal_minor", sa.BigInteger(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("settlement_method", sa.String(24), nullable=False, server_default="direct_cash"),
        sa.Column("buyer_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("seller_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("buyer_user_id", "idempotency_key", name="uq_commerce_order_idempotency"),
        sa.CheckConstraint("status IN ('placed','accepted','rejected','ready','fulfilled','cancelled')", name="ck_commerce_order_status"),
        sa.CheckConstraint("currency = 'ETB' AND settlement_method = 'direct_cash'", name="ck_commerce_order_settlement_v1"),
        sa.CheckConstraint("subtotal_minor >= 0 AND total_minor >= 0 AND total_minor = subtotal_minor", name="ck_commerce_order_total_v1"),
    )
    op.create_index("ix_commerce_orders_business_status", "commerce_orders", ["business_id", "status"])
    op.create_index("ix_commerce_orders_buyer_created", "commerce_orders", ["buyer_user_id", "created_at"])

    op.create_table(
        "commerce_order_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("commerce_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_item_id", sa.String(36), sa.ForeignKey("commerce_catalog_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sku_snapshot", sa.String(80), nullable=False),
        sa.Column("title_snapshot", sa.String(180), nullable=False),
        sa.Column("unit_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("line_total_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("unit_price_minor >= 0 AND quantity > 0 AND line_total_minor = unit_price_minor * quantity", name="ck_commerce_order_item_totals"),
    )

    op.create_table(
        "commerce_order_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("commerce_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("event_type IN ('placed','accepted','rejected','ready','fulfilled','cancelled')", name="ck_commerce_order_event_type"),
    )
    op.create_index("ix_commerce_order_events_order_created", "commerce_order_events", ["order_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_commerce_order_events_order_created", table_name="commerce_order_events")
    op.drop_table("commerce_order_events")
    op.drop_table("commerce_order_items")
    op.drop_index("ix_commerce_orders_buyer_created", table_name="commerce_orders")
    op.drop_index("ix_commerce_orders_business_status", table_name="commerce_orders")
    op.drop_table("commerce_orders")
    op.drop_table("commerce_cart_items")
    op.drop_index("ix_commerce_carts_buyer", table_name="commerce_carts")
    op.drop_table("commerce_carts")
