from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


def test_migrations_upgrade_and_downgrade_on_sqlite(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    try:
        command.upgrade(config, "head")
        engine = create_engine(f"sqlite:///{database_path}")
        inspector = inspect(engine)
        assert "audit_events" in inspector.get_table_names()
        assert "listing_images" in inspector.get_table_names()
        assert "locations" in inspector.get_table_names()
        assert "reports" in inspector.get_table_names()
        assert "markets" in inspector.get_table_names()
        assert "market_schedule_days" in inspector.get_table_names()
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM markets").scalar_one() == 8
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM market_schedule_days WHERE is_active = 1").scalar_one() == 8
        assert {"is_suspended", "auth_version"} <= {column["name"] for column in inspector.get_columns("users")}
        assert {"listing_id", "seller_id", "reason", "description", "evidence", "status", "previous_target_status", "reviewed_by"} <= {
            column["name"] for column in inspector.get_columns("reports")
        }
        location_columns = {column["name"] for column in inspector.get_columns("locations")}
        assert {"parent_id", "code", "level", "name_en", "name_am", "name_mdy"} <= location_columns
        assert "location_id" in {column["name"] for column in inspector.get_columns("listings")}
        assert {"name_am", "name_mdy"} <= {column["name"] for column in inspector.get_columns("categories")}
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM locations").scalar_one() >= 7
        assert "client_sync_id" in {column["name"] for column in inspector.get_columns("listings")}
        image_columns = {column["name"] for column in inspector.get_columns("listing_images")}
        assert {"client_image_id", "storage_key", "width", "height"} <= image_columns
        inquiry_columns = {column["name"] for column in inspector.get_columns("inquiries")}
        assert {"buyer_user_id", "status", "read_at", "closed_at"} <= inquiry_columns
        assert {"actor_id", "action", "resource_type", "resource_id", "event_metadata"} <= {
            column["name"] for column in inspector.get_columns("audit_events")
        }

        command.downgrade(config, "0004_listing_images_sync")
        inspector = inspect(engine)
        assert "locations" not in inspector.get_table_names()
        assert "markets" not in inspector.get_table_names()
        assert "market_schedule_days" not in inspector.get_table_names()
        assert "location_id" not in {column["name"] for column in inspector.get_columns("listings")}
        assert "reports" not in inspector.get_table_names()
        assert {"is_suspended", "auth_version"}.isdisjoint({column["name"] for column in inspector.get_columns("users")})

        command.downgrade(config, "0003_audit_inquiries")
        inspector = inspect(engine)
        assert "listing_images" not in inspector.get_table_names()
        assert "client_sync_id" not in {column["name"] for column in inspector.get_columns("listings")}

        command.downgrade(config, "0002_moderation")
        inspector = inspect(engine)
        assert "audit_events" not in inspector.get_table_names()
        inquiry_columns = {column["name"] for column in inspector.get_columns("inquiries")}
        assert "buyer_user_id" not in inquiry_columns

        command.downgrade(config, "base")
        assert not {"users", "listings", "inquiries"} & set(inspect(engine).get_table_names())
        engine.dispose()
    finally:
        get_settings.cache_clear()
