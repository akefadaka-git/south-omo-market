import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_postgresql_full_migration_chain_and_append_only_audit_trigger(monkeypatch):
    database_url = os.environ["TEST_POSTGRES_URL"]
    monkeypatch.setenv("DATABASE_URL", database_url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        command.upgrade(config, "head")
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"users", "seller_profiles", "categories", "listings", "inquiries",
                "audit_events", "listing_images", "locations", "reports", "alembic_version"} <= tables
        assert "client_sync_id" in {
            column["name"] for column in inspector.get_columns("listings")
        }
        assert {"client_image_id", "storage_key", "content_type", "size_bytes",
                "width", "height"} <= {
            column["name"] for column in inspector.get_columns("listing_images")
        }
        assert {"parent_id", "code", "level", "name_en", "name_am", "name_mdy"} <= {
            column["name"] for column in inspector.get_columns("locations")
        }
        assert "location_id" in {
            column["name"] for column in inspector.get_columns("listings")
        }
        with engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM locations")).scalar_one() == 7
        assert {"buyer_user_id", "status", "read_at", "closed_at"} <= {
            column["name"] for column in inspector.get_columns("inquiries")
        }
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == "0008_reports_and_seller_blocks"
            assert {"is_suspended", "auth_version"} <= {column["name"] for column in inspector.get_columns("users")}
            report_columns = {column["name"] for column in inspector.get_columns("reports")}
            assert {"reporter_user_id", "listing_id", "seller_id", "reason", "description", "evidence", "status", "review_note"} <= report_columns
            expanded_categories = connection.execute(text("""
                SELECT COUNT(*) FROM categories
                WHERE slug IN (
                    'livestock-camels-pack-animals', 'livestock-beekeeping-products',
                    'agriculture-coffee-cash-crops', 'agriculture-farm-inputs-irrigation',
                    'food-honey-spices-ingredients', 'food-grain-flour',
                    'retail-building-materials', 'retail-solar-energy-batteries',
                    'retail-vehicle-motorcycle-parts', 'services-farm-machinery-irrigation',
                    'services-veterinary-animal-health', 'services-construction-trades',
                    'services-household-personal', 'services-business-digital',
                    'services-transport-local', 'services-education-community',
                    'rentals-event-equipment', 'rentals-workspace-shops',
                    'jobs-hospitality-services', 'jobs-apprenticeships-short-term',
                    'services-farm-labour-crop-care', 'services-livestock-handling-market',
                    'rentals-accommodation-stays', 'jobs-market-retail-work'
                )
            """)).scalar_one()
            assert expanded_categories == 24
            assert connection.execute(text("""
                SELECT COUNT(*) FROM categories
                WHERE json_array_length(attributes_schema) > 0
            """)).scalar_one() >= 43
            trigger = connection.execute(text("""
                SELECT COUNT(*) FROM pg_trigger
                WHERE tgname = 'audit_events_append_only' AND NOT tgisinternal
            """)).scalar_one()
            assert trigger == 1

        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO audit_events
                    (id, actor_id, action, resource_type, resource_id, event_metadata)
                VALUES
                    ('integration-audit-row', NULL, 'integration.test',
                     'integration', 'integration-resource', '{}'::json)
            """))

        with pytest.raises(DBAPIError, match="audit_events are append-only"):
            with engine.begin() as connection:
                connection.execute(text("""
                    UPDATE audit_events SET action = 'tampered'
                    WHERE id = 'integration-audit-row'
                """))

        with pytest.raises(DBAPIError, match="audit_events are append-only"):
            with engine.begin() as connection:
                connection.execute(text("""
                    DELETE FROM audit_events WHERE id = 'integration-audit-row'
                """))

        with engine.connect() as connection:
            assert connection.execute(text("""
                SELECT action FROM audit_events WHERE id = 'integration-audit-row'
            """)).scalar_one() == "integration.test"

        command.downgrade(config, "base")
        remaining = set(inspect(engine).get_table_names())
        assert not {"users", "listings", "inquiries", "audit_events", "listing_images", "locations"} & remaining
        with engine.connect() as connection:
            functions = connection.execute(text("""
                SELECT COUNT(*) FROM pg_proc WHERE proname = 'reject_audit_event_mutation'
            """)).scalar_one()
            assert functions == 0
    finally:
        engine.dispose()
        get_settings.cache_clear()
