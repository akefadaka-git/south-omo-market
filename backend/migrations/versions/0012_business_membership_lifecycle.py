"""Harden business identity, membership lifecycle and seller integration.

Revision ID: 0012_business_membership_lifecycle
Revises: 0011_gov_employment_ai
"""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision = "0012_business_membership_lifecycle"
down_revision = "0011_gov_employment_ai"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        sa.Column("registration_number", sa.String(120), nullable=True),
        sa.Column("registered_address", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(254), nullable=True),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("verification_evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ):
        op.add_column("business_profiles", column)
    op.create_foreign_key("fk_business_profiles_verified_by_users", "business_profiles", "users", ["verified_by"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("business_memberships") as batch:
        batch.drop_constraint("uq_business_membership_user", type_="unique")
        batch.add_column(sa.Column("invited_by", sa.String(36), nullable=True))
        batch.add_column(sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("revoked_by", sa.String(36), nullable=True))
        batch.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        batch.create_foreign_key("fk_business_memberships_invited_by_users", "users", ["invited_by"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_business_memberships_revoked_by_users", "users", ["revoked_by"], ["id"], ondelete="SET NULL")
        batch.create_check_constraint("ck_business_membership_role", "membership_role IN ('owner','administrator','manager','staff','finance','viewer')")
        batch.create_check_constraint("ck_business_membership_status", "status IN ('invited','pending','active','suspended','rejected','revoked','expired')")

    op.create_index(
        "uq_business_membership_current", "business_memberships", ["business_id", "user_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('invited','pending','active','suspended')"),
        postgresql_where=sa.text("status IN ('invited','pending','active','suspended')"),
    )

    op.create_table(
        "business_membership_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_id", sa.String(36), sa.ForeignKey("business_memberships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_business_membership_events_business_created", "business_membership_events", ["business_id", "created_at"])

    op.create_table(
        "business_verification_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_status", sa.String(24), nullable=True),
        sa.Column("new_status", sa.String(24), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("new_status IN ('pending','verified','rejected','suspended')", name="ck_business_verification_event_status"),
    )
    op.create_index("ix_business_verification_events_business_created", "business_verification_events", ["business_id", "created_at"])

    op.create_table(
        "business_role_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("membership_role", sa.String(40), nullable=False),
        sa.Column("permission_code", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("membership_role", "permission_code", name="uq_business_role_permission"),
        sa.CheckConstraint("membership_role IN ('owner','administrator','manager','staff','finance','viewer')", name="ck_business_role_permission_role"),
    )
    matrix = {
        "owner": ("business.profile.read", "business.profile.manage", "business.member.manage", "marketplace.listing.manage", "commerce.catalog.manage", "commerce.order.manage", "business.finance.read"),
        "administrator": ("business.profile.read", "business.profile.manage", "business.member.manage", "marketplace.listing.manage", "commerce.catalog.manage", "commerce.order.manage"),
        "manager": ("business.profile.read", "marketplace.listing.manage", "commerce.catalog.manage", "commerce.order.manage"),
        "staff": ("business.profile.read", "marketplace.listing.manage", "commerce.order.manage"),
        "finance": ("business.profile.read", "commerce.order.read", "business.finance.read"),
        "viewer": ("business.profile.read", "commerce.order.read"),
    }
    for role, permissions in matrix.items():
        for permission in permissions:
            op.get_bind().execute(sa.text("""
                INSERT INTO business_role_permissions (id, membership_role, permission_code)
                VALUES (:id, :role, :permission)
                ON CONFLICT (membership_role, permission_code) DO NOTHING
            """), {
                "id": str(uuid5(NAMESPACE_URL, f"south-omo-market:business-role:{role}:{permission}")),
                "role": role, "permission": permission,
            })

    op.add_column("seller_profiles", sa.Column("business_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_seller_profiles_business_id", "seller_profiles", "business_profiles", ["business_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_seller_profiles_business_id", "seller_profiles", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_seller_profiles_business_id", table_name="seller_profiles")
    op.drop_constraint("fk_seller_profiles_business_id", "seller_profiles", type_="foreignkey")
    op.drop_column("seller_profiles", "business_id")
    op.drop_table("business_role_permissions")
    op.drop_index("ix_business_verification_events_business_created", table_name="business_verification_events")
    op.drop_table("business_verification_events")
    op.drop_index("ix_business_membership_events_business_created", table_name="business_membership_events")
    op.drop_table("business_membership_events")
    op.drop_index("uq_business_membership_current", table_name="business_memberships")
    with op.batch_alter_table("business_memberships") as batch:
        batch.drop_constraint("ck_business_membership_status", type_="check")
        batch.drop_constraint("ck_business_membership_role", type_="check")
        batch.drop_constraint("fk_business_memberships_revoked_by_users", type_="foreignkey")
        batch.drop_constraint("fk_business_memberships_invited_by_users", type_="foreignkey")
        batch.drop_column("updated_at")
        batch.drop_column("expires_at")
        batch.drop_column("revoked_at")
        batch.drop_column("revoked_by")
        batch.drop_column("accepted_at")
        batch.drop_column("invited_at")
        batch.drop_column("invited_by")
        batch.create_unique_constraint("uq_business_membership_user", ["business_id", "user_id"])
    op.drop_constraint("fk_business_profiles_verified_by_users", "business_profiles", type_="foreignkey")
    for column in ("updated_at", "suspended_at", "verified_at", "verified_by", "verification_notes", "verification_evidence", "contact_phone", "contact_email", "registered_address", "registration_number"):
        op.drop_column("business_profiles", column)
