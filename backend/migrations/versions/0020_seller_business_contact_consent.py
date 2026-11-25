"""Require verified seller businesses and explicit inquiry contact consent.

Revision ID: 0020_seller_business_contact_consent
Revises: 0019_account_intent_bilingual_markets
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_seller_business_contact_consent"
down_revision = "0019_bilingual_market_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("inquiries") as batch:
        batch.alter_column(
            "contact_value",
            existing_type=sa.String(length=160),
            nullable=True,
        )
        batch.add_column(
            sa.Column(
                "contact_disclosure_consent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(
            sa.Column("contact_consent_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    # Existing records without affirmative consent intentionally remain
    # non-disclosing; downgrade restores the old NOT NULL contract using a
    # non-contact placeholder for rows where consent was not granted.
    op.execute(
        "UPDATE inquiries SET contact_value = 'not-shared' WHERE contact_value IS NULL"
    )
    with op.batch_alter_table("inquiries") as batch:
        batch.drop_column("contact_consent_at")
        batch.drop_column("contact_disclosure_consent")
        batch.alter_column(
            "contact_value",
            existing_type=sa.String(length=160),
            nullable=False,
        )
