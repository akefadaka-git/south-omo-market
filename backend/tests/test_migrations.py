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
        assert {"roles", "permissions", "role_permissions", "user_roles", "user_permissions"} <= set(inspector.get_table_names())
        assert {"business_membership_events", "business_verification_events", "business_role_permissions"} <= set(inspector.get_table_names())
        assert {"registration_number", "verification_evidence", "verified_by", "verified_at", "updated_at"} <= {column["name"] for column in inspector.get_columns("business_profiles")}
        assert {"invited_by", "accepted_at", "revoked_at", "expires_at", "updated_at"} <= {column["name"] for column in inspector.get_columns("business_memberships")}
        assert "business_id" in {column["name"] for column in inspector.get_columns("seller_profiles")}
        assert {"employment_providers", "job_seeker_profiles", "employment_opportunities", "employment_advertisements", "advertising_agreements", "advertising_payments", "employment_applications", "candidate_consents", "candidate_referrals", "employment_events"} <= set(inspector.get_table_names())
        assert {"policy_packs", "policy_rules", "ai_providers", "ai_models", "ai_task_routes",
                "protected_category_roots"} <= set(inspector.get_table_names())
        assert "description" in {column["name"] for column in inspector.get_columns("markets")}
        assert {"effective_from", "effective_until"} <= {column["name"] for column in inspector.get_columns("market_schedule_days")}
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM markets").scalar_one() == 8
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM market_schedule_days WHERE is_active = 1").scalar_one() == 8
            actual = connection.exec_driver_sql("""
                SELECT m.name, d.weekday FROM markets m
                JOIN market_schedule_days d ON d.market_id = m.id
                WHERE m.is_active = 1 AND d.is_active = 1 ORDER BY m.name
            """).all()
            assert actual == [
                ("Ajo", 5), ("Asheker", 1), ("Bala", 1), ("Beneta", 3),
                ("Bobo", 2), ("Boshkoro", 5), ("Gento", 5), ("Koybe", 0),
            ]
            assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0016_commerce_cart_orders"

        command.downgrade(config, "0008_reports_and_seller_blocks")
        command.upgrade(config, "head")
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



def test_business_membership_migration_preserves_legacy_rows_and_allows_history(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "business-lifecycle.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "0011_gov_employment_ai")
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO users (id, phone_number, display_name, password_hash, is_active, is_admin, is_suspended, auth_version) "
                "VALUES ('legacy-user', '+251900000901', 'Legacy Seller', 'synthetic-hash', 1, 0, 0, 0)"
            )
            connection.exec_driver_sql(
                "INSERT INTO business_profiles (id, business_code, legal_name, display_name, business_type, verification_status, is_active) "
                "VALUES ('legacy-business', 'LEGACY-BIZ-001', 'Legacy Business PLC', 'Legacy Shop', 'retail', 'pending', 1)"
            )
            connection.exec_driver_sql(
                "INSERT INTO business_memberships (id, business_id, user_id, membership_role, status) "
                "VALUES ('legacy-membership', 'legacy-business', 'legacy-user', 'owner', 'pending')"
            )
            connection.exec_driver_sql(
                "INSERT INTO seller_profiles (id, user_id, public_name, location_label) "
                "VALUES ('legacy-seller', 'legacy-user', 'Legacy Shop', 'Koybe')"
            )
        command.upgrade(config, "head")
        with engine.begin() as connection:
            legacy = connection.exec_driver_sql(
                "SELECT business_code, verification_status FROM business_profiles WHERE id='legacy-business'"
            ).one()
            assert tuple(legacy) == ("LEGACY-BIZ-001", "pending")
            membership = connection.exec_driver_sql(
                "SELECT membership_role, status FROM business_memberships WHERE id='legacy-membership'"
            ).one()
            assert tuple(membership) == ("owner", "pending")
            assert connection.exec_driver_sql(
                "SELECT business_id FROM seller_profiles WHERE id='legacy-seller'"
            ).scalar_one() is None
            connection.exec_driver_sql(
                "UPDATE business_memberships SET status='revoked', revoked_at=CURRENT_TIMESTAMP "
                "WHERE id='legacy-membership'"
            )
            connection.exec_driver_sql(
                "INSERT INTO business_memberships (id, business_id, user_id, membership_role, status) "
                "VALUES ('replacement-membership', 'legacy-business', 'legacy-user', 'owner', 'pending')"
            )
            assert connection.exec_driver_sql(
                "SELECT COUNT(*) FROM business_memberships WHERE business_id='legacy-business' AND user_id='legacy-user'"
            ).scalar_one() == 2
            assert connection.exec_driver_sql(
                "SELECT COUNT(*) FROM business_role_permissions WHERE membership_role='owner'"
            ).scalar_one() >= 7
    finally:
        engine.dispose()
        get_settings.cache_clear()
