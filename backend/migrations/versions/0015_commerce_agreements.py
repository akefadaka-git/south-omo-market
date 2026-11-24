"""Add versioned, auditable commerce agreements.

Revision ID: 0015_commerce_agreements
Revises: 0014_commerce_catalog_inventory
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_commerce_agreements"
down_revision = "0014_commerce_catalog_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commerce_agreements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("counterparty_business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("counterparty_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("agreement_type", sa.String(40), nullable=False),
        sa.Column("agreement_code", sa.String(80), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("terms_text", sa.Text(), nullable=False),
        sa.Column("terms_sha256", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("business_id", "agreement_code", "version", name="uq_commerce_agreement_version"),
        sa.CheckConstraint("agreement_type IN ('seller_terms','buyer_terms','trade_terms','service_terms')", name="ck_commerce_agreement_type"),
        sa.CheckConstraint("status IN ('draft','offered','accepted','rejected','revoked','expired')", name="ck_commerce_agreement_status"),
        sa.CheckConstraint("currency = 'ETB'", name="ck_commerce_agreement_currency_v1"),
        sa.CheckConstraint("(counterparty_business_id IS NOT NULL) OR (counterparty_user_id IS NOT NULL)", name="ck_commerce_agreement_counterparty"),
        sa.CheckConstraint("counterparty_business_id IS NULL OR counterparty_user_id IS NULL", name="ck_commerce_agreement_single_counterparty"),
    )
    op.create_index("ix_commerce_agreements_business_status", "commerce_agreements", ["business_id", "status"])

    op.create_table(
        "commerce_agreement_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agreement_id", sa.String(36), sa.ForeignKey("commerce_agreements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("event_type IN ('created','offered','accepted','rejected','revoked','expired')", name="ck_commerce_agreement_event_type"),
    )
    op.create_index("ix_commerce_agreement_events_agreement_created", "commerce_agreement_events", ["agreement_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_commerce_agreement_events_agreement_created", table_name="commerce_agreement_events")
    op.drop_table("commerce_agreement_events")
    op.drop_index("ix_commerce_agreements_business_status", table_name="commerce_agreements")
    op.drop_table("commerce_agreements")
