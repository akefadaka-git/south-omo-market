from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.seeders.system_reference import seed_system_reference_data
from app.policy_engine import evaluate_policy


def test_governance_migration_and_reference_seeder_are_repeatable(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "governance-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(f"sqlite:///{database_path}")
        with Session(engine) as db:
            seed_system_reference_data(db)
            seed_system_reference_data(db)
            assert db.execute(text("SELECT COUNT(*) FROM roles")).scalar_one() == 6
            assert db.execute(text("SELECT COUNT(*) FROM permissions")).scalar_one() == 17
            assert db.execute(text("""
                SELECT COUNT(*) FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE r.code = 'owner' AND p.code = 'employment.advertisement.publish'
            """)).scalar_one() == 1
            assert db.execute(text("""
                SELECT COUNT(*) FROM role_permissions rp
                JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id
                WHERE r.code='owner' AND p.code='business.verification.manage'
            """)).scalar_one() == 1
            assert db.execute(text("""
                SELECT COUNT(*) FROM role_permissions rp
                JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id
                WHERE r.code='admin' AND p.code='business.verification.manage'
            """)).scalar_one() == 0
            assert db.execute(text("""
                SELECT COUNT(*) FROM user_roles ur JOIN roles r ON r.id = ur.role_id
                WHERE r.code = 'owner'
            """)).scalar_one() == 0
            iroka = db.execute(text("""
                SELECT primary_provider, enabled, endpoint_configured
                FROM ai_providers WHERE code = 'iroka'
            """)).one()
            assert iroka == (1, 0, 0) or iroka == (True, False, False)
            assert db.execute(text("""
                SELECT status FROM policy_packs WHERE code = 'south-omo-default-deny'
            """)).scalar_one() == "active"
            assert db.execute(text("""
                SELECT effect FROM policy_rules
                WHERE rule_code = 'employment-advertisement-publish-owner-only'
            """)).scalar_one() == "allow"
            assert evaluate_policy(
                db,
                subject="role:owner",
                action="employment.advertisement.publish",
                resource="employment_advertisements",
                facts={"provider_verified": True, "agreement_accepted": True, "payment_verified": True},
            )
            assert not evaluate_policy(
                db,
                subject="role:owner",
                action="employment.advertisement.publish",
                resource="employment_advertisements",
                facts={"provider_verified": True, "agreement_accepted": True, "payment_verified": False},
            )
            assert db.execute(text("""
                SELECT COUNT(*) FROM ai_task_routes
                WHERE enabled = 0 AND requires_human_approval = 1 AND quota_per_day = 0
            """)).scalar_one() == 4
            # A repeat run must repair drift in system-owned grants and policy definitions.
            db.execute(text("""
                INSERT INTO role_permissions (role_id,permission_id)
                SELECT r.id,p.id FROM roles r,permissions p
                WHERE r.code='admin' AND p.code='business.verification.manage'
            """))
            db.execute(text("""
                UPDATE policy_packs SET status='disabled'
                WHERE code='south-omo-default-deny'
            """))
            db.execute(text("""
                UPDATE policy_rules SET effect='deny',subject='*'
                WHERE rule_code='employment-advertisement-publish-owner-only'
            """))
            seed_system_reference_data(db)
            assert db.execute(text("""
                SELECT COUNT(*) FROM role_permissions rp
                JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id
                WHERE r.code='admin' AND p.code='business.verification.manage'
            """)).scalar_one() == 0
            assert db.execute(text("""
                SELECT status FROM policy_packs WHERE code='south-omo-default-deny'
            """)).scalar_one() == "active"
            assert db.execute(text("""
                SELECT effect,subject FROM policy_rules
                WHERE rule_code='employment-advertisement-publish-owner-only'
            """)).one() == ("allow","role:owner")
        engine.dispose()
    finally:
        get_settings.cache_clear()
