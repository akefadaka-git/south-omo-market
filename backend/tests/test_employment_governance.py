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

def test_withdraw_consent_revokes_all_active_consents_for_that_provider() -> None:
    from app.routers.employment import withdraw_candidate_sharing_consent

    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE employment_applications "
                "(id TEXT PRIMARY KEY, job_seeker_id TEXT, opportunity_id TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE job_seeker_profiles "
                "(id TEXT PRIMARY KEY, user_id TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE employment_opportunities "
                "(id TEXT PRIMARY KEY, provider_id TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE candidate_consents "
                "(id TEXT PRIMARY KEY, job_seeker_id TEXT, provider_id TEXT, "
                "purpose TEXT, withdrawn_at TEXT)"
            )
            connection.execute(text(
                "INSERT INTO job_seeker_profiles (id, user_id) VALUES ('profile-1', 'candidate-1')"
            ))
            connection.execute(text(
                "INSERT INTO employment_opportunities (id, provider_id) "
                "VALUES ('opportunity-1', 'provider-1')"
            ))
            connection.execute(text(
                "INSERT INTO employment_applications (id, job_seeker_id, opportunity_id) "
                "VALUES ('application-1', 'profile-1', 'opportunity-1')"
            ))
            connection.execute(text(
                "INSERT INTO candidate_consents "
                "(id, job_seeker_id, provider_id, purpose, withdrawn_at) VALUES "
                "('consent-1', 'profile-1', 'provider-1', 'application review', NULL), "
                "('consent-2', 'profile-1', 'provider-1', 'candidate matching', NULL), "
                "('consent-3', 'profile-1', 'provider-2', 'unrelated provider', NULL)"
            ))

        with Session(engine) as db:
            result = withdraw_candidate_sharing_consent(
                "application-1",
                user=SimpleNamespace(id="candidate-1"),
                db=db,
            )
            assert result["status"] == "withdrawn"
            assert result["withdrawn_count"] == 2
            assert set(result["withdrawn_consent_ids"]) == {"consent-1", "consent-2"}
            assert db.execute(text(
                "SELECT COUNT(*) FROM candidate_consents "
                "WHERE provider_id = 'provider-1' AND withdrawn_at IS NOT NULL"
            )).scalar_one() == 2
            assert db.execute(text(
                "SELECT COUNT(*) FROM candidate_consents "
                "WHERE provider_id = 'provider-2' AND withdrawn_at IS NULL"
            )).scalar_one() == 1
    finally:
        engine.dispose()

def test_authenticated_provider_request_stays_pending_until_owner_verification() -> None:
    from app.routers.employment import ProviderRequest, request_employment_provider

    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE business_profiles "
                "(id TEXT PRIMARY KEY, business_code TEXT UNIQUE, legal_name TEXT, "
                "display_name TEXT, business_type TEXT, verification_status TEXT, is_active BOOLEAN)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE business_memberships "
                "(id TEXT PRIMARY KEY, business_id TEXT, user_id TEXT, membership_role TEXT, status TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE employment_providers "
                "(id TEXT PRIMARY KEY, business_id TEXT UNIQUE, verification_status TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE employment_events "
                "(id TEXT PRIMARY KEY, actor_id TEXT, event_type TEXT, resource_type TEXT, "
                "resource_id TEXT, event_metadata JSON)"
            )

        with Session(engine) as db:
            payload = ProviderRequest(
                business_code="SOM-PROVIDER-001",
                legal_name="Synthetic Provider PLC",
                display_name="Synthetic Provider",
                business_type="recruitment_agency",
            )
            result = request_employment_provider(
                payload,
                user=SimpleNamespace(id="provider-user-1"),
                db=db,
            )
            assert result["verification_status"] == "pending"
            assert db.execute(text(
                "SELECT verification_status FROM employment_providers WHERE id = :id"
            ), {"id": result["provider_id"]}).scalar_one() == "pending"
            assert db.execute(text(
                "SELECT status FROM business_memberships WHERE business_id = :id"
            ), {"id": result["business_id"]}).scalar_one() == "pending"
            assert db.execute(text(
                "SELECT verification_status FROM business_profiles WHERE id = :id"
            ), {"id": result["business_id"]}).scalar_one() == "pending"
            assert db.execute(text(
                "SELECT event_type FROM employment_events WHERE resource_id = :id"
            ), {"id": result["provider_id"]}).scalar_one() == "employment.provider.requested"

            with pytest.raises(HTTPException) as error:
                request_employment_provider(
                    payload,
                    user=SimpleNamespace(id="provider-user-1"),
                    db=db,
                )
            assert error.value.status_code == 409
            assert db.execute(text("SELECT COUNT(*) FROM employment_providers")).scalar_one() == 1
    finally:
        engine.dispose()

