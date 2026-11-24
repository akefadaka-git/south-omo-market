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
                "audit_events", "listing_images", "locations", "reports", "markets", "market_schedule_days", "alembic_version"} <= tables
        assert {
            "roles", "permissions", "role_permissions", "user_roles", "user_permissions",
            "business_profiles", "business_memberships", "employment_providers",
            "job_seeker_profiles", "employment_opportunities", "employment_advertisements",
            "advertising_agreements", "advertising_payments", "employment_applications",
            "candidate_consents", "candidate_referrals", "employment_events",
            "policy_packs", "policy_rules", "ai_providers", "ai_models", "ai_task_routes",
        } <= tables
        assert "description" in {column["name"] for column in inspector.get_columns("markets")}
        assert {"effective_from", "effective_until"} <= {column["name"] for column in inspector.get_columns("market_schedule_days")}
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
            assert revision == "0011_gov_employment_ai"
            assert connection.execute(text("SELECT COUNT(*) FROM markets")).scalar_one() == 8
            assert connection.execute(text("SELECT COUNT(*) FROM market_schedule_days WHERE is_active = TRUE")).scalar_one() == 8
            expected_markets = {
                "Beneta": 3, "Asheker": 1, "Boshkoro": 5, "Bala": 1,
                "Koybe": 0, "Bobo": 2, "Ajo": 5, "Gento": 5,
            }
            actual_markets = dict(connection.execute(text("""
                SELECT m.name, d.weekday FROM markets m
                JOIN market_schedule_days d ON d.market_id = m.id
                WHERE m.is_active = TRUE AND d.is_active = TRUE
            """)).all())
            assert actual_markets == expected_markets
            assert {"is_suspended", "auth_version"} <= {column["name"] for column in inspector.get_columns("users")}
            report_columns = {column["name"] for column in inspector.get_columns("reports")}
            assert {"reporter_user_id", "listing_id", "seller_id", "reason", "description", "evidence", "status", "review_note", "previous_target_status"} <= report_columns
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
        assert not {"users", "listings", "inquiries", "audit_events", "listing_images", "locations", "markets", "market_schedule_days"} & remaining
        with engine.connect() as connection:
            functions = connection.execute(text("""
                SELECT COUNT(*) FROM pg_proc WHERE proname = 'reject_audit_event_mutation'
            """)).scalar_one()
            assert functions == 0
    finally:
        engine.dispose()
        get_settings.cache_clear()

@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_postgresql_owner_controlled_employment_advertising_lifecycle(monkeypatch):
    database_url = os.environ["TEST_POSTGRES_URL"]
    monkeypatch.setenv("DATABASE_URL", database_url)
    from app.core.config import get_settings
    from sqlalchemy.orm import Session
    from fastapi import HTTPException
    from app.models import User
    from app.seeders.system_reference import seed_system_reference_data
    from app.routers.employment import (
        AgreementAcceptance,
        OwnerAdvertisementCreate,
        PaymentSubmission,
        PaymentVerification,
        ProviderRequest,
        accept_advertising_agreement,
        create_owner_managed_advertisement,
        list_published_employment_advertisements,
        publish_employment_advertisement,
        request_employment_provider,
        submit_advertising_payment_evidence,
        verify_advertising_payment,
        verify_employment_provider,
    )

    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    engine = create_engine(database_url, pool_pre_ping=True)
    upgraded = False
    try:
        command.upgrade(config, "head")
        upgraded = True
        with Session(engine) as db:
            provider_user = User(
                id="synthetic-provider-user",
                phone_number="+251900000101",
                display_name="Synthetic Provider",
                password_hash="synthetic-test-hash",
                is_active=True,
                is_admin=False,
            )
            owner = User(
                id="synthetic-owner-user",
                phone_number="+251900000102",
                display_name="Synthetic Owner",
                password_hash="synthetic-test-hash",
                is_active=True,
                is_admin=False,
            )
            db.add_all([provider_user, owner])
            db.commit()
            seed_system_reference_data(db)

            request = request_employment_provider(
                ProviderRequest(
                    business_code="SYNTHETIC-EMPLOYER-001",
                    legal_name="Synthetic Employer PLC",
                    display_name="Synthetic Employer",
                    business_type="recruitment_agency",
                ),
                user=provider_user,
                db=db,
            )
            assert request["verification_status"] == "pending"
            membership_status = db.execute(text("""
                SELECT status FROM business_memberships
                WHERE business_id = :business_id AND user_id = :user_id
            """), {"business_id": request["business_id"], "user_id": provider_user.id}).scalar_one()
            assert membership_status == "pending"

            verified = verify_employment_provider(request["provider_id"], owner=owner, db=db)
            assert verified["verification_status"] == "verified"
            membership_status = db.execute(text("""
                SELECT status FROM business_memberships
                WHERE business_id = :business_id AND user_id = :user_id
            """), {"business_id": request["business_id"], "user_id": provider_user.id}).scalar_one()
            assert membership_status == "active"

            advertisement = create_owner_managed_advertisement(
                OwnerAdvertisementCreate(
                    provider_id=request["provider_id"],
                    title="Synthetic agricultural worker",
                    description="Synthetic employment opportunity for integration testing.",
                    occupation_code="AGRICULTURE",
                    location_code="KOYBE",
                    employment_type="full_time",
                    requirements=[{"code": "experience", "minimum_years": 1}],
                    agreed_price_minor=10000,
                    duration_days=30,
                    terms_version="TEST-1",
                ),
                owner=owner,
                db=db,
            )
            accepted = accept_advertising_agreement(
                advertisement["agreement_id"],
                AgreementAcceptance(acceptance_evidence="Synthetic acceptance evidence"),
                user=provider_user,
                db=db,
            )
            assert accepted["status"] == "accepted"

            first_payment = submit_advertising_payment_evidence(
                advertisement["agreement_id"],
                PaymentSubmission(
                    amount_minor=4000,
                    currency="ETB",
                    payment_method="bank_transfer",
                    evidence_ref="synthetic://receipt/first",
                ),
                user=provider_user,
                db=db,
            )
            verify_advertising_payment(
                advertisement["advertisement_id"],
                first_payment["payment_id"],
                PaymentVerification(verification_note="Synthetic evidence checked"),
                owner=owner,
                db=db,
            )
            with pytest.raises(HTTPException) as underpayment:
                publish_employment_advertisement(advertisement["advertisement_id"], owner=owner, db=db)
            assert underpayment.value.status_code == 409

            second_payment = submit_advertising_payment_evidence(
                advertisement["agreement_id"],
                PaymentSubmission(
                    amount_minor=6000,
                    currency="ETB",
                    payment_method="bank_transfer",
                    evidence_ref="synthetic://receipt/second",
                ),
                user=provider_user,
                db=db,
            )
            verify_advertising_payment(
                advertisement["advertisement_id"],
                second_payment["payment_id"],
                PaymentVerification(verification_note="Synthetic second evidence checked"),
                owner=owner,
                db=db,
            )
            published = publish_employment_advertisement(advertisement["advertisement_id"], owner=owner, db=db)
            assert published["status"] == "published"
            public_ads = list_published_employment_advertisements(db=db)
            assert len(public_ads) == 1
            assert public_ads[0]["title"] == "Synthetic agricultural worker"
            assert public_ads[0]["location_code"] == "KOYBE"
    finally:
        if upgraded:
            command.downgrade(config, "base")
        engine.dispose()
        get_settings.cache_clear()

