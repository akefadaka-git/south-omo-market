"""Add account intent and bilingual market details.

Revision ID: 0019_bilingual_market_roles
Revises: 0018_seller_business_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_bilingual_market_roles"
down_revision = "0018_seller_business_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(32), nullable=False, server_default="buyer"),
    )
    with op.batch_alter_table("users") as batch:
        batch.create_check_constraint(
            "ck_users_account_type",
            "account_type IN ('buyer','merchant','bulk_distributor','producer','service_provider','other')",
        )

    op.add_column("markets", sa.Column("name_en", sa.String(120), nullable=True))
    op.add_column("markets", sa.Column("name_am", sa.String(120), nullable=True))
    op.add_column("markets", sa.Column("description_en", sa.Text(), nullable=True))
    op.add_column("markets", sa.Column("description_am", sa.Text(), nullable=True))
    op.add_column("markets", sa.Column("address_en", sa.String(500), nullable=True))
    op.add_column("markets", sa.Column("address_am", sa.String(500), nullable=True))
    op.add_column("markets", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("markets", sa.Column("longitude", sa.Float(), nullable=True))

    # Preserve legacy market names as English display names. Do not invent
    # Amharic translations for historical records; they remain explicitly
    # incomplete until verified by an authorized data steward.
    op.execute("UPDATE markets SET name_en = name WHERE name_en IS NULL")
    with op.batch_alter_table("markets") as batch:
        batch.create_check_constraint(
            "ck_markets_coordinates_pair",
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
        )
        batch.create_check_constraint(
            "ck_markets_coordinates_range",
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90) AND "
            "(longitude IS NULL OR longitude BETWEEN -180 AND 180)",
        )


def downgrade() -> None:
    with op.batch_alter_table("markets") as batch:
        batch.drop_constraint("ck_markets_coordinates_range", type_="check")
        batch.drop_constraint("ck_markets_coordinates_pair", type_="check")
    for column in (
        "longitude", "latitude", "address_am", "address_en",
        "description_am", "description_en", "name_am", "name_en",
    ):
        op.drop_column("markets", column)
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_account_type", type_="check")
        batch.drop_column("account_type")
