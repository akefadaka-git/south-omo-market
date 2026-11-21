"""Expand South Omo Market catalogue coverage and category attribute schemas."""

from alembic import op
import sqlalchemy as sa

revision = "0007_catalogue_expansion"
down_revision = "0006_category_attributes"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    def field(key: str, kind: str, required: bool = False, **rules: object) -> dict[str, object]:
        return {"key": key, "type": kind, "required": required, **rules}

    def category(number: int, slug: str, name: str, parent: int,
                 schema: list[dict[str, object]]) -> dict[str, object]:
        return {
            "id": f"40000000-0000-4000-8000-{number:012d}",
            "slug": slug,
            "name_en": name,
            "name_am": None,
            "name_mdy": None,
            "parent_id": f"00000000-0000-4000-8000-{parent:012d}",
            "attributes_schema": schema,
            "is_active": True,
        }

    text = lambda key, required=False, maximum=160: field(
        key, "text", required, max_length=maximum
    )
    number = lambda key, required=False, minimum=0, maximum=None: field(
        key, "number", required, **({"min": minimum} if minimum is not None else {}),
        **({"max": maximum} if maximum is not None else {})
    )
    choice = lambda key, options, required=False: field(
        key, "choice", required, options=options
    )

    rows = [
        category(1, "livestock-camels-pack-animals", "Camels and pack animals", 1, [
            choice("species", ["camel", "donkey", "mule", "other"], True),
            choice("sex", ["female", "male"], False),
            number("count", True, 1),
            number("age_years", False, 0, 60),
        ]),
        category(2, "livestock-beekeeping-products", "Beekeeping products and equipment", 1, [
            choice("product_type", ["honey", "beeswax", "beehive", "colony", "equipment"], True),
            number("quantity", True, 0),
            choice("unit", ["kg", "piece", "set", "litre"], True),
        ]),
        category(3, "agriculture-coffee-cash-crops", "Coffee and cash crops", 2, [
            text("crop", True, 80),
            number("quantity", True, 0),
            choice("unit", ["kg", "quintal", "ton", "bag"], True),
            choice("grade", ["ungraded", "grade_1", "grade_2", "grade_3", "other"], False),
        ]),
        category(4, "agriculture-farm-inputs-irrigation", "Farm inputs and irrigation supplies", 2, [
            text("product", True, 120),
            text("brand_model", False, 120),
            choice("condition", ["new", "used", "refurbished"], True),
        ]),
        category(5, "food-honey-spices-ingredients", "Honey, spices and cooking ingredients", 3, [
            text("product", True, 100),
            number("quantity", True, 0),
            choice("unit", ["kg", "gram", "litre", "piece", "pack"], True),
        ]),
        category(6, "food-grain-flour", "Grain, flour and milling products", 3, [
            text("product", True, 100),
            number("quantity", True, 0),
            choice("unit", ["kg", "quintal", "ton", "bag"], True),
        ]),
        category(7, "retail-building-materials", "Building materials and fittings", 4, [
            text("product", True, 120),
            text("material_type", False, 80),
            choice("condition", ["new", "used", "refurbished"], True),
            number("quantity", False, 0),
        ]),
        category(8, "retail-solar-energy-batteries", "Solar lamps, kits and batteries", 4, [
            text("brand_model", False, 120),
            choice("product_type", ["solar_lamp", "solar_kit", "battery", "inverter", "other"], True),
            choice("condition", ["new", "used", "refurbished"], True),
            number("warranty_months", False, 0, 120),
        ]),
        category(9, "retail-vehicle-motorcycle-parts", "Bicycle, motorcycle and vehicle parts", 4, [
            text("part_name", True, 120),
            text("compatible_model", False, 120),
            choice("condition", ["new", "used", "refurbished"], True),
        ]),
        category(10, "services-farm-machinery-irrigation", "Farm machinery and irrigation services", 5, [
            text("service_area", True, 160),
            choice("service_type", ["ploughing", "tractor_hire", "irrigation_install", "irrigation_repair", "harvesting", "other"], True),
            number("experience_years", False, 0, 80),
            choice("price_basis", ["hour", "day", "task", "negotiable"], True),
        ]),
        category(11, "services-veterinary-animal-health", "Veterinary and animal-health services", 5, [
            text("service_area", True, 160),
            text("qualification_or_license", False, 160),
            choice("service_type", ["consultation", "vaccination", "treatment", "other"], True),
        ]),
        category(12, "services-construction-trades", "Construction, carpentry and trades", 5, [
            text("service_area", True, 160),
            text("trade", True, 80),
            number("experience_years", False, 0, 80),
            choice("price_basis", ["hour", "day", "task", "negotiable"], True),
        ]),
        category(13, "services-household-personal", "Household and personal services", 5, [
            text("service_area", True, 160),
            text("service_type", True, 100),
            choice("availability", ["weekdays", "weekends", "flexible"], False),
        ]),
        category(14, "services-business-digital", "Business, IT and digital services", 5, [
            text("service_area", True, 160),
            text("service_type", True, 100),
            number("experience_years", False, 0, 80),
        ]),
        category(15, "services-transport-local", "Local passenger transport services", 5, [
            text("service_area", True, 160),
            choice("vehicle_type", ["motorcycle", "car", "minibus", "truck", "other"], True),
            choice("price_basis", ["trip", "hour", "day", "negotiable"], True),
        ]),
        category(16, "services-education-community", "Tutoring, training and community services", 5, [
            text("service_area", True, 160),
            text("subject_or_skill", True, 120),
            number("experience_years", False, 0, 80),
        ]),
        category(17, "rentals-event-equipment", "Event equipment and furniture rentals", 6, [
            text("asset", True, 120),
            choice("rental_period", ["hourly", "daily", "weekly"], True),
            number("deposit_minor", False, 0),
            choice("condition", ["good", "fair", "needs_repair"], False),
        ]),
        category(18, "rentals-workspace-shops", "Shop and workspace rentals", 6, [
            choice("property_type", ["shop", "office", "workshop", "storage", "other"], True),
            choice("rental_period", ["monthly", "yearly"], True),
            number("rooms_or_units", False, 1),
        ]),
        category(19, "jobs-hospitality-services", "Hospitality and service work", 7, [
            text("employer", True, 160),
            text("role", True, 120),
            choice("pay_basis", ["daily", "weekly", "monthly", "task"], True),
            choice("schedule", ["full_time", "part_time", "seasonal", "temporary"], True),
        ]),
        category(20, "jobs-apprenticeships-short-term", "Apprenticeships and short-term work", 7, [
            text("employer", True, 160),
            text("role_or_skill", True, 120),
            choice("pay_basis", ["unpaid_training", "daily", "weekly", "monthly", "task"], True),
            text("duration", False, 80),
        ]),
    ]

    op.bulk_insert(categories, rows)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM categories WHERE slug IN ("
        "'livestock-camels-pack-animals', 'livestock-beekeeping-products', "
        "'agriculture-coffee-cash-crops', 'agriculture-farm-inputs-irrigation', "
        "'food-honey-spices-ingredients', 'food-grain-flour', "
        "'retail-building-materials', 'retail-solar-energy-batteries', "
        "'retail-vehicle-motorcycle-parts', 'services-farm-machinery-irrigation', "
        "'services-veterinary-animal-health', 'services-construction-trades', "
        "'services-household-personal', 'services-business-digital', "
        "'services-transport-local', 'services-education-community', "
        "'rentals-event-equipment', 'rentals-workspace-shops', "
        "'jobs-hospitality-services', 'jobs-apprenticeships-short-term'"
        ")"
    ))
