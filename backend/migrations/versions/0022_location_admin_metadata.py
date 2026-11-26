"""Add bilingual location metadata, coordinates and discovery tags.

Revision ID: 0022_location_admin_metadata
Revises: 0021_listing_edit_versions
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_location_admin_metadata"
down_revision = "0021_listing_edit_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("description_en", sa.Text(), nullable=True))
    op.add_column("locations", sa.Column("description_am", sa.Text(), nullable=True))
    op.add_column("locations", sa.Column("address_en", sa.String(length=500), nullable=True))
    op.add_column("locations", sa.Column("address_am", sa.String(length=500), nullable=True))
    op.add_column("locations", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("locations", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "locations",
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("locations", "tags")
    op.drop_column("locations", "longitude")
    op.drop_column("locations", "latitude")
    op.drop_column("locations", "address_am")
    op.drop_column("locations", "address_en")
    op.drop_column("locations", "description_am")
    op.drop_column("locations", "description_en")
