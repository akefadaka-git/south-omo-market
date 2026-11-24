"""Add localized categories and normalized South Omo geography."""
from alembic import op
import sqlalchemy as sa

revision = "0005_localized_geography"
down_revision = "0004_listing_images_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("level", sa.String(24), nullable=False),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("name_am", sa.String(120), nullable=True),
        sa.Column("name_mdy", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.create_index("ix_locations_code", "locations", ["code"], unique=True)
    op.create_index("ix_locations_level", "locations", ["level"])
    op.add_column("categories", sa.Column("name_am", sa.String(120), nullable=True))
    op.add_column("categories", sa.Column("name_mdy", sa.String(120), nullable=True))
    with op.batch_alter_table("listings") as batch:
        batch.add_column(sa.Column("location_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_listings_location_id_locations", "locations", ["location_id"], ["id"]
        )
        batch.create_index("ix_listings_location_id", ["location_id"])

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE categories SET name_am = :name WHERE id = :id"), [
        {"id": "00000000-0000-4000-8000-000000000001", "name": "እንስሳት"},
        {"id": "00000000-0000-4000-8000-000000000002", "name": "ግብርና"},
        {"id": "00000000-0000-4000-8000-000000000003", "name": "ምግብ እና ግሮሰሪ"},
        {"id": "00000000-0000-4000-8000-000000000004", "name": "ሱቆች እና ምርቶች"},
        {"id": "00000000-0000-4000-8000-000000000005", "name": "አገልግሎቶች"},
        {"id": "00000000-0000-4000-8000-000000000006", "name": "ንብረት፣ መሳሪያ እና ኪራይ"},
    ])

    locations = sa.table(
        "locations", sa.column("id", sa.String(36)), sa.column("parent_id", sa.String(36)),
        sa.column("code", sa.String(80)), sa.column("level", sa.String(24)),
        sa.column("name_en", sa.String(120)), sa.column("name_am", sa.String(120)),
        sa.column("name_mdy", sa.String(120)), sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(locations, [
        {"id": "10000000-0000-4000-8000-000000000001", "parent_id": None, "code": "ET-SO", "level": "zone", "name_en": "South Omo", "name_am": "ደቡብ ኦሞ", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000002", "parent_id": "10000000-0000-4000-8000-000000000001", "code": "ET-SO-MAALE", "level": "woreda", "name_en": "Maale", "name_am": "ማሌ", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000003", "parent_id": "10000000-0000-4000-8000-000000000002", "code": "ET-SO-MAALE-KOYBE", "level": "locality", "name_en": "Koybe", "name_am": "ቆይቤ", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000004", "parent_id": "10000000-0000-4000-8000-000000000001", "code": "ET-SO-JINKA", "level": "town", "name_en": "Jinka", "name_am": "ጂንካ", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000005", "parent_id": "10000000-0000-4000-8000-000000000001", "code": "ET-SO-KEYAFER", "level": "town", "name_en": "Key Afer", "name_am": "ቀይ አፈር", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000006", "parent_id": "10000000-0000-4000-8000-000000000001", "code": "ET-SO-TURMI", "level": "town", "name_en": "Turmi", "name_am": "ቱርሚ", "name_mdy": None, "is_active": True},
        {"id": "10000000-0000-4000-8000-000000000007", "parent_id": "10000000-0000-4000-8000-000000000001", "code": "ET-SO-DIMEKA", "level": "town", "name_en": "Dimeka", "name_am": "ዲመካ", "name_mdy": None, "is_active": True},
    ])


def downgrade() -> None:
    with op.batch_alter_table("listings") as batch:
        batch.drop_index("ix_listings_location_id")
        batch.drop_constraint("fk_listings_location_id_locations", type_="foreignkey")
        batch.drop_column("location_id")
    with op.batch_alter_table("categories") as batch:
        batch.drop_column("name_mdy")
        batch.drop_column("name_am")
    op.drop_index("ix_locations_level", table_name="locations")
    op.drop_index("ix_locations_code", table_name="locations")
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_table("locations")
