"""Persist Owner-governed category publication boundaries.

Revision ID: 0013_governance_hardening
Revises: 0012_business_lifecycle
"""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision = "0013_governance_hardening"
down_revision = "0012_business_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protected_category_roots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "category_id", sa.String(36),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("policy_code", sa.String(100), nullable=False, unique=True),
        sa.Column("applies_to_descendants", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("seller_listing_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("category_id", "policy_code", name="uq_protected_category_policy"),
    )
    op.create_index(
        "ix_protected_category_roots_category",
        "protected_category_roots",
        ["category_id"],
    )

    bind = op.get_bind()
    roots = bind.execute(
        sa.text("SELECT id FROM categories WHERE slug = :slug"),
        {"slug": "work-opportunities"},
    ).scalars().all()
    for category_id in roots:
        bind.execute(
            sa.text("""
                INSERT INTO protected_category_roots
                    (id, category_id, policy_code, applies_to_descendants, seller_listing_allowed)
                VALUES (:id, :category_id, :policy_code, TRUE, FALSE)
                ON CONFLICT (category_id, policy_code) DO NOTHING
            """),
            {
                "id": str(uuid5(NAMESPACE_URL, f"south-omo-market:protected-category:{category_id}:employment-agency")),
                "category_id": category_id,
                "policy_code": "employment-agency-owner-controlled",
            },
        )


def downgrade() -> None:
    op.drop_index("ix_protected_category_roots_category", table_name="protected_category_roots")
    op.drop_table("protected_category_roots")
