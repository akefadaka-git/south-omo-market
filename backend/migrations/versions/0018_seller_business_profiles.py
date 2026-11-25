"""Extend business profiles for seller onboarding and public business details.

Revision ID: 0018_seller_business_profiles
Revises: 0017_customer_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_seller_business_profiles"
down_revision = "0017_customer_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("business_profiles") as batch:
        batch.alter_column("legal_name", existing_type=sa.String(200), nullable=True)
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("primary_category_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("operating_location_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("service_area", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch.add_column(sa.Column("operating_hours", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch.add_column(sa.Column("supported_languages", sa.JSON(), nullable=False, server_default=sa.text("'[\\"am\\",\\"en\\"]'")))
        batch.add_column(sa.Column("public_contact_phone", sa.String(32), nullable=True))
        batch.add_column(sa.Column("public_contact_email", sa.String(254), nullable=True))
        batch.add_column(sa.Column("public_contact_method", sa.String(16), nullable=True))
        batch.add_column(sa.Column("public_location_visibility", sa.String(16), nullable=False, server_default="hidden"))
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("location_consent_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_business_profiles_primary_category", "categories",
            ["primary_category_id"], ["id"], ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_business_profiles_operating_location", "locations",
            ["operating_location_id"], ["id"], ondelete="SET NULL",
        )
        batch.create_check_constraint(
            "ck_business_public_contact_method",
            "public_contact_method IS NULL OR public_contact_method IN ('phone','sms','email')",
        )
        batch.create_check_constraint(
            "ck_business_public_location_visibility",
            "public_location_visibility IN ('hidden','approximate','exact')",
        )
        batch.create_check_constraint(
            "ck_business_public_coordinates_pair",
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_business_public_coordinates_range",
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90) AND (longitude IS NULL OR longitude BETWEEN -180 AND 180)",
        )
        batch.create_check_constraint(
            "ck_business_exact_location_consent",
            "public_location_visibility != 'exact' OR (latitude IS NOT NULL AND longitude IS NOT NULL AND location_consent_at IS NOT NULL)",
        )

    op.create_index("ix_business_profiles_primary_category_id", "business_profiles", ["primary_category_id"])
    op.create_index("ix_business_profiles_operating_location_id", "business_profiles", ["operating_location_id"])


def downgrade() -> None:
    op.drop_index("ix_business_profiles_operating_location_id", table_name="business_profiles")
    op.drop_index("ix_business_profiles_primary_category_id", table_name="business_profiles")
    with op.batch_alter_table("business_profiles") as batch:
        batch.drop_constraint("ck_business_exact_location_consent", type_="check")
        batch.drop_constraint("ck_business_public_coordinates_range", type_="check")
        batch.drop_constraint("ck_business_public_coordinates_pair", type_="check")
        batch.drop_constraint("ck_business_public_location_visibility", type_="check")
        batch.drop_constraint("ck_business_public_contact_method", type_="check")
        batch.drop_constraint("fk_business_profiles_operating_location", type_="foreignkey")
        batch.drop_constraint("fk_business_profiles_primary_category", type_="foreignkey")
        batch.drop_column("location_consent_at")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
        batch.drop_column("public_location_visibility")
        batch.drop_column("public_contact_method")
        batch.drop_column("public_contact_email")
        batch.drop_column("public_contact_phone")
        batch.drop_column("supported_languages")
        batch.drop_column("operating_hours")
        batch.drop_column("service_area")
        batch.drop_column("operating_location_id")
        batch.drop_column("primary_category_id")
        batch.drop_column("description")
        batch.alter_column("legal_name", existing_type=sa.String(200), nullable=False)
