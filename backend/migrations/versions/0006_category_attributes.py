"""Add hierarchical categories and structured listing attributes."""
from alembic import op
import sqlalchemy as sa

revision = "0006_category_attributes"
down_revision = "0005_localized_geography"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("parent_id", sa.String(36), nullable=True))
    op.add_column("categories", sa.Column("attributes_schema", sa.JSON(), nullable=False, server_default="[]"))
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories", "categories", ["parent_id"], ["id"],
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.add_column("listings", sa.Column("attributes", sa.JSON(), nullable=False, server_default="{}"))

    categories = sa.table(
        "categories",
        sa.column("id", sa.String(36)),
        sa.column("slug", sa.String(80)),
        sa.column("name_en", sa.String(120)),
        sa.column("name_am", sa.String(120)),
        sa.column("name_mdy", sa.String(120)),
        sa.column("parent_id", sa.String(36)),
        sa.column("attributes_schema", sa.JSON()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(categories, [
        {"id": "00000000-0000-4000-8000-000000000007", "slug": "work-opportunities", "name_en": "Work opportunities", "name_am": None, "name_mdy": None, "parent_id": None, "attributes_schema": [], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000001", "slug": "livestock-cattle", "name_en": "Cattle", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000001", "attributes_schema": [{"key": "sex", "type": "choice", "required": True, "options": ["female", "male"]}, {"key": "age_months", "type": "number", "required": False, "min": 0, "max": 600}, {"key": "health_notes", "type": "text", "required": False, "max_length": 500}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000002", "slug": "livestock-goats-sheep", "name_en": "Goats and sheep", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000001", "attributes_schema": [{"key": "species", "type": "choice", "required": True, "options": ["goat", "sheep"]}, {"key": "sex", "type": "choice", "required": False, "options": ["female", "male"]}, {"key": "age_months", "type": "number", "required": False, "min": 0, "max": 360}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000003", "slug": "livestock-poultry", "name_en": "Poultry and eggs", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000001", "attributes_schema": [{"key": "poultry_type", "type": "choice", "required": True, "options": ["chicken", "duck", "other"]}, {"key": "quantity", "type": "number", "required": True, "min": 1}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000004", "slug": "livestock-dairy", "name_en": "Milk and dairy", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000001", "attributes_schema": [{"key": "product", "type": "text", "required": True, "max_length": 80}, {"key": "quantity", "type": "number", "required": True, "min": 0}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000005", "slug": "agriculture-grains", "name_en": "Cereals and grains", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000002", "attributes_schema": [{"key": "crop", "type": "choice", "required": True, "options": ["maize", "sorghum", "teff", "wheat", "barley", "other"]}, {"key": "quantity", "type": "number", "required": True, "min": 0}, {"key": "unit", "type": "choice", "required": True, "options": ["kg", "quintal", "ton"]}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000006", "slug": "agriculture-pulses-oilseeds", "name_en": "Pulses and oilseeds", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000002", "attributes_schema": [{"key": "crop", "type": "text", "required": True, "max_length": 80}, {"key": "quantity", "type": "number", "required": True, "min": 0}, {"key": "unit", "type": "choice", "required": True, "options": ["kg", "quintal", "ton"]}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000007", "slug": "agriculture-fruits-vegetables", "name_en": "Fruits and vegetables", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000002", "attributes_schema": [{"key": "produce", "type": "text", "required": True, "max_length": 80}, {"key": "quantity", "type": "number", "required": True, "min": 0}, {"key": "unit", "type": "choice", "required": True, "options": ["kg", "basket", "piece"]}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000008", "slug": "agriculture-seeds-feed", "name_en": "Seeds, seedlings and animal feed", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000002", "attributes_schema": [{"key": "product", "type": "text", "required": True, "max_length": 100}, {"key": "quantity", "type": "number", "required": False, "min": 0}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000009", "slug": "food-groceries", "name_en": "Groceries and household consumables", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000003", "attributes_schema": [{"key": "product_type", "type": "text", "required": True, "max_length": 100}, {"key": "package_size", "type": "text", "required": False, "max_length": 80}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000010", "slug": "food-prepared", "name_en": "Prepared foods and non-alcoholic drinks", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000003", "attributes_schema": [{"key": "item_type", "type": "text", "required": True, "max_length": 100}, {"key": "made_on", "type": "text", "required": False, "max_length": 40}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000011", "slug": "retail-clothing", "name_en": "Clothing, shoes and accessories", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000004", "attributes_schema": [{"key": "condition", "type": "choice", "required": True, "options": ["new", "used", "refurbished"]}, {"key": "size", "type": "text", "required": False, "max_length": 40}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000012", "slug": "retail-electronics", "name_en": "Phones and electronics", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000004", "attributes_schema": [{"key": "brand_model", "type": "text", "required": False, "max_length": 120}, {"key": "condition", "type": "choice", "required": True, "options": ["new", "used", "refurbished"]}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000013", "slug": "retail-household-tools", "name_en": "Household goods and tools", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000004", "attributes_schema": [{"key": "condition", "type": "choice", "required": True, "options": ["new", "used", "refurbished"]}, {"key": "brand_model", "type": "text", "required": False, "max_length": 120}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000014", "slug": "services-agriculture-livestock", "name_en": "Agriculture and livestock services", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000005", "attributes_schema": [{"key": "service_area", "type": "text", "required": True, "max_length": 160}, {"key": "experience_years", "type": "number", "required": False, "min": 0, "max": 80}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000015", "slug": "services-trades-repair", "name_en": "Trades, construction and repair", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000005", "attributes_schema": [{"key": "service_area", "type": "text", "required": True, "max_length": 160}, {"key": "experience_years", "type": "number", "required": False, "min": 0, "max": 80}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000016", "slug": "services-personal-business", "name_en": "Personal and business services", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000005", "attributes_schema": [{"key": "service_area", "type": "text", "required": True, "max_length": 160}, {"key": "experience_years", "type": "number", "required": False, "min": 0, "max": 80}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000017", "slug": "rentals-property", "name_en": "Property and accommodation rentals", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000006", "attributes_schema": [{"key": "rental_period", "type": "choice", "required": True, "options": ["daily", "weekly", "monthly", "yearly"]}, {"key": "condition", "type": "text", "required": False, "max_length": 300}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000018", "slug": "rentals-equipment", "name_en": "Equipment and machinery rentals", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000006", "attributes_schema": [{"key": "rental_period", "type": "choice", "required": True, "options": ["hourly", "daily", "weekly"]}, {"key": "asset_condition", "type": "text", "required": False, "max_length": 300}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000019", "slug": "jobs-farm-seasonal", "name_en": "Farm and seasonal work", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000007", "attributes_schema": [{"key": "employer", "type": "text", "required": True, "max_length": 160}, {"key": "pay_basis", "type": "choice", "required": True, "options": ["daily", "weekly", "monthly", "task"]}, {"key": "closing_date", "type": "text", "required": False, "max_length": 40}], "is_active": True},
        {"id": "30000000-0000-4000-8000-000000000020", "slug": "jobs-shop-trade", "name_en": "Shop and skilled trade work", "name_am": None, "name_mdy": None, "parent_id": "00000000-0000-4000-8000-000000000007", "attributes_schema": [{"key": "employer", "type": "text", "required": True, "max_length": 160}, {"key": "pay_basis", "type": "choice", "required": True, "options": ["daily", "weekly", "monthly", "task"]}, {"key": "closing_date", "type": "text", "required": False, "max_length": 40}], "is_active": True},
    ])


def downgrade() -> None:
    op.drop_column("listings", "attributes")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.drop_column("categories", "attributes_schema")
    op.drop_column("categories", "parent_id")
