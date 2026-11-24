import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.governance import require_business_permission
from app.models import Category
from app.policy_engine import evaluate_policy
from app.routers.listings import _require_leaf_category


def test_policy_wildcards_and_explicit_deny_precedence():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE policy_packs (id TEXT PRIMARY KEY, status TEXT)")
        conn.exec_driver_sql("""CREATE TABLE policy_rules (
            id TEXT PRIMARY KEY, policy_pack_id TEXT, effect TEXT, subject TEXT,
            action TEXT, resource TEXT, conditions JSON)""")
        conn.exec_driver_sql("INSERT INTO policy_packs VALUES ('p','active')")
        conn.exec_driver_sql("""INSERT INTO policy_rules VALUES
            ('allow','p','allow','*','*','*','{}'),
            ('deny','p','deny','role:merchant','marketplace.listing.create','listings','{}')""")
    try:
        with Session(engine) as db:
            assert evaluate_policy(
                db, subject="role:customer", action="marketplace.listing.read",
                resource="listings", facts={},
            )
            assert not evaluate_policy(
                db, subject="role:merchant", action="marketplace.listing.create",
                resource="listings", facts={},
            )
    finally:
        engine.dispose()


def test_policy_malformed_conditions_fail_closed():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE policy_packs (id TEXT PRIMARY KEY, status TEXT)")
        conn.exec_driver_sql("""CREATE TABLE policy_rules (
            id TEXT PRIMARY KEY, policy_pack_id TEXT, effect TEXT, subject TEXT,
            action TEXT, resource TEXT, conditions JSON)""")
        conn.exec_driver_sql("INSERT INTO policy_packs VALUES ('p','active')")
        conn.exec_driver_sql("""INSERT INTO policy_rules VALUES
            ('bad','p','allow','*','read','listings','not-json')""")
    try:
        with Session(engine) as db:
            assert not evaluate_policy(
                db, subject="role:customer", action="read",
                resource="listings", facts={},
            )
    finally:
        engine.dispose()


def test_persisted_protected_category_root_blocks_renamed_descendants():
    engine = create_engine("sqlite://")
    Category.__table__.create(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("""CREATE TABLE protected_category_roots (
            id TEXT PRIMARY KEY, category_id TEXT, policy_code TEXT,
            applies_to_descendants BOOLEAN, seller_listing_allowed BOOLEAN)""")
        conn.exec_driver_sql("""INSERT INTO categories
            (id,slug,name_en,name_am,name_mdy,parent_id,attributes_schema,is_active)
            VALUES ('root','employment-root-renamed','Employment','ሥራ',NULL,NULL,'[]',1),
                   ('child','employment-child','Seasonal work','ወቅታዊ ሥራ',NULL,'root','[]',1)""")
        conn.exec_driver_sql("""INSERT INTO protected_category_roots
            VALUES ('policy-root','root','employment-agency-owner-controlled',1,0)""")
    try:
        with Session(engine) as db:
            category = db.get(Category, "child")
            with pytest.raises(HTTPException) as err:
                _require_leaf_category(db, category)
            assert err.value.status_code == 403
    finally:
        engine.dispose()


def test_business_permission_requires_verified_active_business_and_active_user():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("""CREATE TABLE users (
            id TEXT PRIMARY KEY, is_active BOOLEAN, is_suspended BOOLEAN)""")
        conn.exec_driver_sql("""CREATE TABLE business_profiles (
            id TEXT PRIMARY KEY, is_active BOOLEAN, verification_status TEXT)""")
        conn.exec_driver_sql("""CREATE TABLE business_memberships (
            business_id TEXT, user_id TEXT, membership_role TEXT, status TEXT, expires_at DATETIME)""")
        conn.exec_driver_sql("""CREATE TABLE business_role_permissions (
            membership_role TEXT, permission_code TEXT)""")
        conn.exec_driver_sql("INSERT INTO users VALUES ('u','1','0')")
        conn.exec_driver_sql("INSERT INTO business_profiles VALUES ('b','1','pending')")
        conn.exec_driver_sql("INSERT INTO business_memberships VALUES ('b','u','manager','active',NULL)")
        conn.exec_driver_sql("INSERT INTO business_role_permissions VALUES ('manager','business.profile.read')")
    try:
        with Session(engine) as db:
            dependency = require_business_permission("business.profile.read")
            with pytest.raises(HTTPException) as pending:
                dependency(business_id="b", user=type("U", (), {"id": "u"})(), db=db)
            assert pending.value.status_code == 403
            db.execute(text("UPDATE business_profiles SET verification_status='verified' WHERE id='b'"))
            db.execute(text("UPDATE users SET is_suspended=TRUE WHERE id='u'"))
            with pytest.raises(HTTPException) as suspended:
                dependency(business_id="b", user=type("U", (), {"id": "u"})(), db=db)
            assert suspended.value.status_code == 403
    finally:
        engine.dispose()
