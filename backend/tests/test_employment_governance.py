from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.governance import require_permission
from app.models import Category
from app.core.database import Base
from app.routers.listings import _require_leaf_category


def test_employment_category_and_descendants_are_blocked_from_seller_listings() -> None:
    engine = create_engine("sqlite://")
    Category.__table__.create(engine)
    try:
        with Session(engine) as db:
            root = Category(id="work-root", slug="work-opportunities", name_en="Work", attributes_schema=[], is_active=True)
            child = Category(id="work-child", slug="farm-seasonal", name_en="Farm", parent_id=root.id, attributes_schema=[], is_active=True)
            leaf = Category(id="work-leaf", slug="seasonal-farm", name_en="Seasonal farm", parent_id=child.id, attributes_schema=[], is_active=True)
            db.add_all([root, child, leaf])
            db.commit()
            with pytest.raises(HTTPException) as error:
                _require_leaf_category(db, leaf)
            assert error.value.status_code == 403
    finally:
        engine.dispose()


def test_owner_only_permission_cannot_be_granted_to_admin_or_direct_user_override() -> None:
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE roles (id TEXT PRIMARY KEY, code TEXT)")
            connection.exec_driver_sql("CREATE TABLE permissions (id TEXT PRIMARY KEY, code TEXT)")
            connection.exec_driver_sql("CREATE TABLE role_permissions (role_id TEXT, permission_id TEXT)")
            connection.exec_driver_sql("CREATE TABLE user_roles (user_id TEXT, role_id TEXT, expires_at TEXT)")
            connection.exec_driver_sql("CREATE TABLE user_permissions (user_id TEXT, permission_id TEXT, granted BOOLEAN)")
            connection.exec_driver_sql("INSERT INTO roles VALUES ('r-admin', 'admin'), ('r-owner', 'owner')")
            connection.exec_driver_sql("INSERT INTO permissions VALUES ('p-publish', 'employment.advertisement.publish')")
            connection.exec_driver_sql("INSERT INTO role_permissions VALUES ('r-admin', 'p-publish'), ('r-owner', 'p-publish')")
            connection.exec_driver_sql("INSERT INTO user_roles VALUES ('u1', 'r-admin', NULL)")
            connection.exec_driver_sql("INSERT INTO user_permissions VALUES ('u1', 'p-publish', 1)")
        with Session(engine) as db:
            dependency = require_permission("employment.advertisement.publish")
            with pytest.raises(HTTPException) as error:
                dependency(user=SimpleNamespace(id="u1"), db=db)
            assert error.value.status_code == 403
            db.execute(text("INSERT INTO user_roles (user_id, role_id, expires_at) VALUES ('u1', 'r-owner', NULL)"))
            db.commit()
            assert dependency(user=SimpleNamespace(id="u1"), db=db).id == "u1"
    finally:
        engine.dispose()



def test_legacy_employment_category_draft_cannot_be_submitted(monkeypatch) -> None:
    from app.routers import listings as listings_router

    category = Category(
        id="legacy-work", slug="work-opportunities", name_en="Work",
        attributes_schema=[], is_active=True,
    )
    listing = SimpleNamespace(id="legacy-listing", category_id=category.id, status="draft")

    class FakeDB:
        committed = False

        def get(self, model, identifier):
            assert model is Category
            assert identifier == category.id
            return category

        def commit(self):
            self.committed = True

    db = FakeDB()
    monkeypatch.setattr(listings_router, "_owned_listing", lambda db, user, listing_id: listing)

    with pytest.raises(HTTPException) as error:
        listings_router.submit_my_listing("legacy-listing", user=SimpleNamespace(id="seller-1"), db=db)

    assert error.value.status_code == 403
    assert listing.status == "draft"
    assert db.committed is False
