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
            "business_profiles", "business_memberships", "business_membership_events", "business_verification_events", "business_role_permissions", "employment_providers",
            "job_seeker_profiles", "employment_opportunities", "employment_advertisements",
            "advertising_agreements", "advertising_payments", "employment_applications",
            "candidate_consents", "candidate_referrals", "employment_events",
            "policy_packs", "policy_rules", "ai_providers", "ai_models", "ai_task_routes",
            "protected_category_roots",
        } <= tables
        assert "description" in {column["name"] for column in inspector.get_columns("markets")}
        assert {"effective_from", "effective_until"} <= {column["name"] for column in inspector.get_columns("market_schedule_days")}
        assert "business_id" in {column["name"] for column in inspector.get_columns("seller_profiles")}
        business_profile_columns = {column["name"] for column in inspector.get_columns("business_profiles")}
        assert {
            "description", "primary_category_id", "operating_location_id", "service_area",
            "operating_hours", "supported_languages", "public_contact_phone",
            "public_contact_email", "public_contact_method", "public_location_visibility",
            "latitude", "longitude", "location_consent_at",
        } <= business_profile_columns
        assert {"registration_number", "verification_evidence", "verified_by", "verified_at", "updated_at"} <= {column["name"] for column in inspector.get_columns("business_profiles")}
        assert {"invited_by", "accepted_at", "revoked_at", "expires_at", "updated_at"} <= {column["name"] for column in inspector.get_columns("business_memberships")}
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
        assert {"user_id", "preferred_location_id", "preferred_market_id", "preferred_language", "email", "contact_preference"} <= {
            column["name"] for column in inspector.get_columns("customer_profiles")
        }
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == "0020_seller_contact_consent"
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
        CandidateConsentRequest,
        OwnerAdvertisementCreate,
        PaymentSubmission,
        PaymentVerification,
        ProviderRequest,
        ProviderRejection,
        accept_advertising_agreement,
        apply_to_published_opportunity,
        create_human_review_candidate_referral,
        create_owner_managed_advertisement,
        grant_candidate_sharing_consent,
        list_employment_provider_requests,
        list_owner_managed_advertisements,
        list_consented_candidates,
        list_published_employment_advertisements,
        publish_employment_advertisement,
        reject_employment_provider,
        request_employment_provider,
        submit_advertising_payment_evidence,
        upsert_private_job_seeker_profile,
        verify_advertising_payment,
        verify_employment_provider,
        withdraw_candidate_sharing_consent,
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
            job_seeker_user = User(
                id="synthetic-job-seeker-user",
                phone_number="+251900000104",
                display_name="Synthetic Job Seeker",
                password_hash="synthetic-test-hash",
                is_active=True,
                is_admin=False,
            )
            agent_user = User(
                id="synthetic-agent-user",
                phone_number="+251900000105",
                display_name="Synthetic Agency Agent",
                password_hash="synthetic-test-hash",
                is_active=True,
                is_admin=False,
            )
            db.add_all([provider_user, owner, job_seeker_user, agent_user])
            db.commit()
            seed_system_reference_data(db)
            agent_role_id = db.execute(text(
                "SELECT id FROM roles WHERE code = 'agent'"
            )).scalar_one()
            db.execute(text("""
                INSERT INTO user_roles (user_id, role_id, assigned_by)
                VALUES (:user_id, :role_id, :owner_id)
            """), {"user_id": agent_user.id, "role_id": agent_role_id, "owner_id": owner.id})
            db.commit()

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
            pending_provider_queue = list_employment_provider_requests(status="pending", owner=owner, db=db)
            assert len(pending_provider_queue) == 1
            assert pending_provider_queue[0]["provider_id"] == request["provider_id"]
            assert pending_provider_queue[0]["business_code"] == "SYNTHETIC-EMPLOYER-001"
            assert pending_provider_queue[0]["contact_user_id"] == provider_user.id
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
            first_payment_queue = list_owner_managed_advertisements(status="pending_owner", owner=owner, db=db)
            assert len(first_payment_queue) == 1
            assert first_payment_queue[0]["provider_name"] == "Synthetic Employer"
            assert first_payment_queue[0]["agreement_status"] == "accepted"
            assert first_payment_queue[0]["payments"][0]["payment_id"] == first_payment["payment_id"]
            assert first_payment_queue[0]["verified_payment_minor"] == 0
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
            published_owner_queue = list_owner_managed_advertisements(status="published", owner=owner, db=db)
            assert len(published_owner_queue) == 1
            assert published_owner_queue[0]["advertisement_status"] == "published"
            assert published_owner_queue[0]["verified_payment_minor"] == 10000
            public_ads = list_published_employment_advertisements(db=db)
            assert len(public_ads) == 1
            assert public_ads[0]["title"] == "Synthetic agricultural worker"
            assert public_ads[0]["location_code"] == "KOYBE"

            profile = upsert_private_job_seeker_profile(
                {
                    "skills": ["farm work"],
                    "experience": [{"role": "seasonal farm worker", "years": 2}],
                    "contact_preferences": {"preferred_channel": "phone"},
                },
                user=job_seeker_user,
                db=db,
            )
            assert db.execute(text("""
                SELECT visibility FROM job_seeker_profiles WHERE id = :id
            """), {"id": profile["profile_id"]}).scalar_one() == "private"
            with pytest.raises(HTTPException) as public_profile:
                upsert_private_job_seeker_profile(
                    {"visibility": "public"},
                    user=job_seeker_user,
                    db=db,
                )
            assert public_profile.value.status_code == 422

            opportunity_id = db.execute(text("""
                SELECT opportunity_id FROM employment_advertisements WHERE id = :id
            """), {"id": advertisement["advertisement_id"]}).scalar_one()
            application = apply_to_published_opportunity(
                opportunity_id,
                user=job_seeker_user,
                db=db,
            )
            duplicate_application = apply_to_published_opportunity(
                opportunity_id,
                user=job_seeker_user,
                db=db,
            )
            assert duplicate_application["application_id"] == application["application_id"]

            consent = grant_candidate_sharing_consent(
                application["application_id"],
                CandidateConsentRequest(
                    purpose="provider review",
                    consent_version="TEST-CONSENT-1",
                ),
                user=job_seeker_user,
                db=db,
            )
            assert consent["status"] == "granted"
            second_consent = grant_candidate_sharing_consent(
                application["application_id"],
                CandidateConsentRequest(
                    purpose="candidate contact",
                    consent_version="TEST-CONSENT-2",
                ),
                user=job_seeker_user,
                db=db,
            )
            assert second_consent["status"] == "granted"
            visible_candidates = list_consented_candidates(
                request["provider_id"],
                user=provider_user,
                db=db,
            )
            assert len(visible_candidates) == 1
            assert visible_candidates[0]["profile_id"] == profile["profile_id"]
            assert "contact_preferences" not in visible_candidates[0]
            assert "phone_number" not in visible_candidates[0]

            from app.governance import require_permission

            with pytest.raises(HTTPException) as provider_referral_denied:
                require_permission("employment.candidate.refer")(user=provider_user, db=db)
            assert provider_referral_denied.value.status_code == 403
            assert require_permission("employment.candidate.refer")(user=agent_user, db=db).id == agent_user.id
            referral = create_human_review_candidate_referral(
                application["application_id"],
                user=agent_user,
                db=db,
            )
            assert referral["decision"] == "human_review"
            assert db.execute(text("""
                SELECT decision FROM candidate_referrals WHERE id = :id
            """), {"id": referral["referral_id"]}).scalar_one() == "human_review"

            withdrawn = withdraw_candidate_sharing_consent(
                application["application_id"],
                user=job_seeker_user,
                db=db,
            )
            assert withdrawn["withdrawn_count"] == 2
            assert list_consented_candidates(
                request["provider_id"],
                user=provider_user,
                db=db,
            ) == []
            with pytest.raises(HTTPException) as referral_after_withdrawal:
                create_human_review_candidate_referral(
                    application["application_id"],
                    user=agent_user,
                    db=db,
                )
            assert referral_after_withdrawal.value.status_code == 409

            rejected_provider_user = User(
                id="synthetic-rejected-provider-user",
                phone_number="+251900000103",
                display_name="Synthetic Rejected Provider",
                password_hash="synthetic-test-hash",
                is_active=True,
                is_admin=False,
            )
            db.add(rejected_provider_user)
            db.commit()
            rejected_request = request_employment_provider(
                ProviderRequest(
                    business_code="SYNTHETIC-EMPLOYER-002",
                    legal_name="Synthetic Rejected Employer PLC",
                    display_name="Synthetic Rejected Employer",
                    business_type="recruitment_agency",
                ),
                user=rejected_provider_user,
                db=db,
            )
            pending_queue = list_employment_provider_requests(status="pending", owner=owner, db=db)
            assert [item["provider_id"] for item in pending_queue] == [rejected_request["provider_id"]]
            rejected = reject_employment_provider(
                rejected_request["provider_id"],
                ProviderRejection(reason="Synthetic verification rejection for integration test"),
                owner=owner,
                db=db,
            )
            assert rejected["verification_status"] == "rejected"
            assert db.execute(text("""
                SELECT verification_status FROM business_profiles WHERE id = :id
            """), {"id": rejected_request["business_id"]}).scalar_one() == "rejected"
            assert db.execute(text("""
                SELECT status FROM business_memberships WHERE business_id = :id
            """), {"id": rejected_request["business_id"]}).scalar_one() == "rejected"
            rejected_queue = list_employment_provider_requests(status="rejected", owner=owner, db=db)
            assert [item["provider_id"] for item in rejected_queue] == [rejected_request["provider_id"]]
    finally:
        if upgraded:
            command.downgrade(config, "base")
        engine.dispose()
        get_settings.cache_clear()

