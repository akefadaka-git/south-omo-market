from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


def test_commerce_migrations_upgrade_downgrade_and_reupgrade(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "commerce-migration-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(f"sqlite:///{database_path}")
        expected = {
            "commerce_catalog_items",
            "inventory_balances",
            "inventory_movements",
            "commerce_agreements",
            "commerce_agreement_events",
            "commerce_carts",
            "commerce_cart_items",
            "commerce_orders",
            "commerce_order_items",
            "commerce_order_events",
            "customer_profiles",
        }
        with engine.connect() as connection:
            inspector = inspect(connection)
            assert expected.issubset(set(inspector.get_table_names()))
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one() == "0017_customer_profiles"
            indexes = inspector.get_indexes("commerce_carts")
            active_cart_index = next(
                index for index in indexes
                if index["name"] == "uq_commerce_cart_active_buyer_business"
            )
            assert active_cart_index["unique"] == 1
            assert "status = 'active'" in str(active_cart_index["dialect_options"]["sqlite_where"])
            catalog_constraints = inspector.get_check_constraints("commerce_catalog_items")
            assert any("unit_price_minor >= 0" in item["sqltext"] for item in catalog_constraints)
        command.downgrade(config, "0013_governance_hardening")
        with engine.connect() as connection:
            names = set(inspect(connection).get_table_names())
            assert expected.isdisjoint(names)
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one() == "0013_governance_hardening"
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert expected.issubset(set(inspect(connection).get_table_names()))
            assert connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one() == "0017_customer_profiles"
        engine.dispose()
    finally:
        get_settings.cache_clear()
