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
        assert "client_sync_id" in {column["name"] for column in inspector.get_columns("listings")}
        image_columns = {column["name"] for column in inspector.get_columns("listing_images")}
        assert {"client_image_id", "storage_key", "width", "height"} <= image_columns
        inquiry_columns = {column["name"] for column in inspector.get_columns("inquiries")}
        assert {"buyer_user_id", "status", "read_at", "closed_at"} <= inquiry_columns
        assert {"actor_id", "action", "resource_type", "resource_id", "event_metadata"} <= {
            column["name"] for column in inspector.get_columns("audit_events")
        }

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
