import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.main import app


@pytest.fixture(scope="module")
def commerce_api():
    database_path = Path(__file__).parent / f"commerce-api-{uuid4().hex}.db"
    database_url = f"sqlite:///{database_path}"
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    current = {"user_id": "commerce-owner"}

    with engine.begin() as connection:
        connection.exec_driver_sql("""
            INSERT INTO users
                (id,phone_number,display_name,password_hash,is_active,is_admin,is_suspended,auth_version)
            VALUES
                ('commerce-owner','+251900000801','Commerce Owner','synthetic-hash',1,0,0,0),
                ('commerce-buyer','+251900000802','Commerce Buyer','synthetic-hash',1,0,0,0),
                ('commerce-viewer','+251900000803','Commerce Viewer','synthetic-hash',1,0,0,0),
                ('commerce-outsider','+251900000804','Commerce Outsider','synthetic-hash',1,0,0,0),
                ('commerce-counterparty','+251900000805','Commerce Counterparty','synthetic-hash',1,0,0,0),
                ('commerce-owner-two','+251900000806','Other Business Owner','synthetic-hash',1,0,0,0)
        """)
        connection.exec_driver_sql("""
            INSERT INTO business_profiles
                (id,business_code,legal_name,display_name,business_type,verification_status,is_active)
            VALUES
                ('commerce-business','COM-001','Commerce Test PLC','Commerce Test','retail','verified',1),
                ('commerce-business-two','COM-002','Other Commerce PLC','Other Commerce','retail','verified',1)
        """)
        connection.exec_driver_sql("""
            INSERT INTO business_memberships (id,business_id,user_id,membership_role,status)
            VALUES
                ('commerce-membership-owner','commerce-business','commerce-owner','owner','active'),
                ('commerce-membership-viewer','commerce-business','commerce-viewer','viewer','active'),
                ('commerce-membership-owner-two','commerce-business-two','commerce-owner-two','owner','active')
        """)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_user():
        return SimpleNamespace(id=current["user_id"])

    previous_db_override = app.dependency_overrides.get(get_db)
    previous_user_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)

    class Context:
        def __init__(self):
            self.client = client
            self.engine = engine
            self.current = current
            with TestingSession() as db:
                self.category_id = db.execute(
                    text("SELECT id FROM categories WHERE is_active=TRUE ORDER BY id LIMIT 1")
                ).scalar_one()

        def as_user(self, user_id):
            self.current["user_id"] = user_id

    context = Context()
    try:
        yield context
    finally:
        if previous_db_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_db_override
        if previous_user_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_user_override
        engine.dispose()
        get_settings.cache_clear()
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        database_path.unlink(missing_ok=True)


def _create_catalog(api, sku: str):
    response = api.client.post(
        "/api/v1/commerce/businesses/commerce-business/catalog",
        json={
            "category_id": api.category_id,
            "sku": sku,
            "title": "Synthetic commerce item",
            "description": "Test-only item",
            "unit_price_minor": 12500,
            "currency": "ETB",
            "unit": "item",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _adjust_stock(api, item_id: str, delta: int, key: str):
    return api.client.post(
        f"/api/v1/commerce/businesses/commerce-business/catalog/{item_id}/inventory",
        json={
            "quantity_delta": delta,
            "movement_type": "receipt" if delta > 0 else "adjustment",
            "reason": "Synthetic regression test stock movement",
            "idempotency_key": key,
        },
    )


def test_catalog_inventory_isolation_atomicity_and_idempotency(commerce_api):
    api = commerce_api
    api.as_user("commerce-owner")
    item_id = _create_catalog(api, "SKU-" + uuid4().hex[:10].upper())

    receipt_key = "receipt-" + uuid4().hex[:12]
    receipt = _adjust_stock(api, item_id, 8, receipt_key)
    assert receipt.status_code == 201, receipt.text
    movement_id = receipt.json()["movement_id"]
    assert receipt.json()["quantity_on_hand"] == 8
    assert receipt.json()["replayed"] is False

    replay = _adjust_stock(api, item_id, 8, receipt_key)
    assert replay.status_code == 201, replay.text
    assert replay.json()["movement_id"] == movement_id
    assert replay.json()["replayed"] is True

    blocked = _adjust_stock(api, item_id, -9, "adjust-" + uuid4().hex[:12])
    assert blocked.status_code == 409

    api.as_user("commerce-owner-two")
    cross_business = api.client.post(
        "/api/v1/commerce/businesses/commerce-business/catalog",
        json={
            "category_id": api.category_id, "sku": "CROSS-" + uuid4().hex[:8],
            "title": "Cross-business item", "unit_price_minor": 1, "currency": "ETB",
        },
    )
    assert cross_business.status_code == 403

    api.as_user("commerce-outsider")
    denied = api.client.post(
        "/api/v1/commerce/businesses/commerce-business/catalog",
        json={
            "category_id": api.category_id, "sku": "UNAUTHORIZED-" + uuid4().hex[:8],
            "title": "Unauthorized item", "unit_price_minor": 1, "currency": "ETB",
        },
    )
    assert denied.status_code == 403

    with api.engine.connect() as connection:
        balance = connection.execute(text("""
            SELECT quantity_on_hand,quantity_reserved FROM inventory_balances
            WHERE catalog_item_id=:item
        """), {"item": item_id}).one()
        ledger = connection.execute(text("""
            SELECT id,movement_type,quantity_delta FROM inventory_movements
            WHERE catalog_item_id=:item
        """), {"item": item_id}).all()
    assert tuple(balance) == (8, 0)
    assert len(ledger) == 1
    assert ledger[0][0] == movement_id
    assert tuple(ledger[0][1:]) == ("receipt", 8)


def test_checkout_reservation_fulfillment_and_order_read_authorization(commerce_api):
    api = commerce_api
    api.as_user("commerce-owner")
    item_id = _create_catalog(api, "ORDER-" + uuid4().hex[:10].upper())
    receipt = _adjust_stock(api, item_id, 5, "stock-" + uuid4().hex[:12])
    assert receipt.status_code == 201, receipt.text

    api.as_user("commerce-buyer")
    cart = api.client.post("/api/v1/commerce/businesses/commerce-business/carts")
    assert cart.status_code == 201, cart.text
    cart_id = cart.json()["id"]
    put = api.client.put(
        f"/api/v1/commerce/carts/{cart_id}/items",
        json={"catalog_item_id": item_id, "quantity": 2},
    )
    assert put.status_code == 200, put.text
    key = "checkout-" + uuid4().hex[:16]
    checkout = api.client.post(
        f"/api/v1/commerce/carts/{cart_id}/checkout",
        params={"idempotency_key": key},
    )
    assert checkout.status_code == 201, checkout.text
    order_id = checkout.json()["order_id"]
    assert checkout.json()["settlement_method"] == "direct_cash"
    assert checkout.json()["total_minor"] == 25000

    replay = api.client.post(
        f"/api/v1/commerce/carts/{cart_id}/checkout",
        params={"idempotency_key": key},
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["order_id"] == order_id
    assert replay.json()["replayed"] is True

    with api.engine.connect() as connection:
        reserved = connection.execute(text("""
            SELECT quantity_on_hand,quantity_reserved FROM inventory_balances
            WHERE catalog_item_id=:item
        """), {"item": item_id}).one()
        reservation = connection.execute(text("""
            SELECT movement_type,quantity_delta,reference_id FROM inventory_movements
            WHERE catalog_item_id=:item AND movement_type='reservation'
        """), {"item": item_id}).one()
        placed_event = connection.execute(text("""
            SELECT event_metadata FROM commerce_order_events
            WHERE order_id=:order AND event_type='placed'
        """), {"order": order_id}).scalar_one()
    assert tuple(reserved) == (5, 2)
    assert tuple(reservation) == ("reservation", 2, order_id)
    if isinstance(placed_event, str):
        placed_event = json.loads(placed_event)
    assert placed_event["settlement_method"] == "direct_cash"

    api.as_user("commerce-viewer")
    visible = api.client.get(f"/api/v1/commerce/orders/{order_id}")
    assert visible.status_code == 200, visible.text
    with api.engine.begin() as connection:
        connection.execute(text("""
            UPDATE business_memberships SET expires_at='2000-01-01 00:00:00'
            WHERE id='commerce-membership-viewer'
        """))
    expired = api.client.get(f"/api/v1/commerce/orders/{order_id}")
    assert expired.status_code == 404
    api.as_user("commerce-outsider")
    hidden = api.client.get(f"/api/v1/commerce/orders/{order_id}")
    assert hidden.status_code == 404

    api.as_user("commerce-owner")
    for status in ("accepted", "ready", "fulfilled"):
        changed = api.client.post(
            f"/api/v1/commerce/businesses/commerce-business/orders/{order_id}/status",
            params={"new_status": status},
        )
        assert changed.status_code == 200, changed.text
    with api.engine.connect() as connection:
        final_balance = connection.execute(text("""
            SELECT quantity_on_hand,quantity_reserved FROM inventory_balances
            WHERE catalog_item_id=:item
        """), {"item": item_id}).one()
        movements = connection.execute(text("""
            SELECT movement_type,quantity_delta FROM inventory_movements
            WHERE catalog_item_id=:item ORDER BY created_at,id
        """), {"item": item_id}).all()
        event_types = connection.execute(text("""
            SELECT event_type FROM commerce_order_events WHERE order_id=:order
            ORDER BY created_at,id
        """), {"order": order_id}).scalars().all()
    assert tuple(final_balance) == (3, 0)
    assert ("reservation", 2) in [tuple(row) for row in movements]
    assert ("fulfillment", -2) in [tuple(row) for row in movements]
    assert set(event_types) == {"placed", "accepted", "ready", "fulfilled"}
    assert len(event_types) == 4

    # A second order is cancelled to prove the release operation is ledgered.
    api.as_user("commerce-buyer")
    cart2 = api.client.post("/api/v1/commerce/businesses/commerce-business/carts")
    assert cart2.status_code == 201, cart2.text
    cart2_id = cart2.json()["id"]
    put2 = api.client.put(
        f"/api/v1/commerce/carts/{cart2_id}/items",
        json={"catalog_item_id": item_id, "quantity": 1},
    )
    assert put2.status_code == 200, put2.text
    checkout2 = api.client.post(
        f"/api/v1/commerce/carts/{cart2_id}/checkout",
        params={"idempotency_key": "checkout-" + uuid4().hex[:16]},
    )
    assert checkout2.status_code == 201, checkout2.text
    order2_id = checkout2.json()["order_id"]
    api.as_user("commerce-owner")
    cancelled = api.client.post(
        f"/api/v1/commerce/businesses/commerce-business/orders/{order2_id}/status",
        params={"new_status": "cancelled"},
    )
    assert cancelled.status_code == 200, cancelled.text
    with api.engine.connect() as connection:
        released = connection.execute(text("""
            SELECT movement_type,quantity_delta,reference_id FROM inventory_movements
            WHERE catalog_item_id=:item AND movement_type='release'
        """), {"item": item_id}).one()
        final_after_cancel = connection.execute(text("""
            SELECT quantity_on_hand,quantity_reserved FROM inventory_balances
            WHERE catalog_item_id=:item
        """), {"item": item_id}).one()
    assert tuple(released) == ("release", -1, order2_id)
    assert tuple(final_after_cancel) == (3, 0)


def test_agreement_decision_is_counterparty_only_and_audited(commerce_api):
    api = commerce_api
    api.as_user("commerce-owner")
    created = api.client.post(
        "/api/v1/commerce/businesses/commerce-business/agreements",
        json={
            "counterparty_user_id": "commerce-counterparty",
            "agreement_type": "trade_terms",
            "agreement_code": "SYNTHETIC-TRADE-" + uuid4().hex[:8],
            "version": "1.0",
            "terms_text": "Synthetic agreement terms for endpoint regression testing.",
        },
    )
    assert created.status_code == 201, created.text
    agreement_id = created.json()["id"]

    api.as_user("commerce-outsider")
    denied = api.client.post(
        f"/api/v1/commerce/agreements/{agreement_id}/decision",
        params={"decision": "accepted"},
    )
    assert denied.status_code == 403

    api.as_user("commerce-counterparty")
    accepted = api.client.post(
        f"/api/v1/commerce/agreements/{agreement_id}/decision",
        params={"decision": "accepted"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    with api.engine.connect() as connection:
        events = connection.execute(text("""
            SELECT event_type FROM commerce_agreement_events
            WHERE agreement_id=:agreement ORDER BY created_at,id
        """), {"agreement": agreement_id}).scalars().all()
    assert set(events) == {"offered", "accepted"}
    assert len(events) == 2



def _seed_published_listing_for_edit(api, listing_id: str) -> str:
    from uuid import uuid4

    with api.engine.begin() as connection:
        seller_id = "seller-edit-test"
        connection.exec_driver_sql(
            """INSERT OR IGNORE INTO seller_profiles
               (id,user_id,business_id,public_name,location_label)
               VALUES (?,'commerce-owner','commerce-business','Edit Test Seller','Koybe')""",
            (seller_id,),
        )
        category_id = connection.execute(text("""
            SELECT c.id FROM categories c
            WHERE c.is_active = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM categories child
                WHERE child.parent_id = c.id AND child.is_active = TRUE
              )
            ORDER BY c.id LIMIT 1
        """)).scalar_one()
        connection.exec_driver_sql(
            """INSERT INTO listings
               (id,seller_id,category_id,title,description,attributes,price_minor,currency,
                location_label,status)
               VALUES (?,?,?,?,?,'{}',?,'ETB','Koybe','published')""",
            (listing_id, seller_id, category_id, "Fresh tomatoes", "Fresh tomatoes from Koybe", 10000),
        )
    return category_id


def test_published_listing_material_edit_stays_private_until_admin_rejects(commerce_api, monkeypatch):
    from fastapi import HTTPException
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import AuditEvent, Listing, ListingEdit, User
    from app.routers import admin as admin_router
    from app.routers import listings as listings_router

    api = commerce_api
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    with Session(api.engine, expire_on_commit=False) as db:
        seller = db.get(User, "commerce-owner")
        submitted = listings_router.update_my_listing(
            listing_id, listings_router.ListingUpdate(price_minor=12500), user=seller, db=db
        )
        assert submitted["edit_status"] == "pending_review"
        assert submitted["changed_fields"] == ["price_minor"]
        public_before = api.client.get(f"/api/v1/listings/{listing_id}")
        assert public_before.status_code == 200, public_before.text
        assert public_before.json()["price_minor"] == 10000

        with pytest.raises(HTTPException) as duplicate:
            listings_router.update_my_listing(
                listing_id, listings_router.ListingUpdate(title="New tomato claim"), user=seller, db=db
            )
        assert duplicate.value.status_code == 409

        edit = db.get(ListingEdit, submitted["edit_id"])
        admin = db.get(User, "commerce-owner")
        rejected = admin_router.decide_listing_edit(
            edit.id, admin_router.ListingEditDecision(decision="reject", note="Not supported"),
            admin=admin, db=db,
        )
        assert rejected["status"] == "rejected"
        db.refresh(db.get(Listing, listing_id))
        current = db.get(Listing, listing_id)
        assert current.status == "published"
        assert current.price_minor == 10000
        assert db.scalar(select(ListingEdit.status).where(ListingEdit.id == edit.id)) == "rejected"
        assert db.scalar(select(AuditEvent.action).where(
            AuditEvent.resource_id == listing_id,
            AuditEvent.action == "listing.edit.rejected",
        )) == "listing.edit.rejected"


def test_admin_approval_applies_pending_material_edit_and_audits(commerce_api, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models import AuditEvent, Listing, ListingEdit, User
    from app.routers import admin as admin_router
    from app.routers import listings as listings_router

    api = commerce_api
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    with Session(api.engine, expire_on_commit=False) as db:
        seller = db.get(User, "commerce-owner")
        submitted = listings_router.update_my_listing(
            listing_id, listings_router.ListingUpdate(price_minor=15000), user=seller, db=db
        )
        edit = db.get(ListingEdit, submitted["edit_id"])
        approved = admin_router.decide_listing_edit(
            edit.id, admin_router.ListingEditDecision(decision="approve", note="Price evidence reviewed"),
            admin=seller, db=db,
        )
        assert approved["status"] == "approved"
        current = db.get(Listing, listing_id)
        assert current.status == "published"
        assert current.price_minor == 15000
        assert db.scalar(select(ListingEdit.pending_key).where(ListingEdit.id == edit.id)) is None
        assert db.scalar(select(AuditEvent.action).where(
            AuditEvent.resource_id == listing_id,
            AuditEvent.action == "listing.edit.approved",
        )) == "listing.edit.approved"


def test_location_id_only_edit_updates_location_label(commerce_api, monkeypatch):
    from sqlalchemy.orm import Session

    from app.models import Listing, ListingEdit, User
    from app.routers import listings as listings_router

    api = commerce_api
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    location_id = str(uuid4())
    with api.engine.begin() as connection:
        connection.exec_driver_sql(
            """INSERT INTO locations (id,code,level,name_en,is_active)
               VALUES (?,'EDIT-LOCATION','woreda','Wolaita Sodo',1)""",
            (location_id,),
        )
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    with Session(api.engine, expire_on_commit=False) as db:
        seller = db.get(User, "commerce-owner")
        submitted = listings_router.update_my_listing(
            listing_id, listings_router.ListingUpdate(location_id=location_id), user=seller, db=db
        )
        assert submitted["edit_status"] == "pending_review"
        edit = db.get(ListingEdit, submitted["edit_id"])
        assert edit.proposed_values["location_id"] == location_id
        assert edit.proposed_values["location_label"] == "Wolaita Sodo"



def test_minor_description_correction_is_published_through_authenticated_api(commerce_api, monkeypatch):
    from app.models import Listing
    from app.routers import listings as listings_router

    api = commerce_api
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    response = api.client.patch(
        f"/api/v1/listings/{listing_id}",
        json={"description": "Fresh tomatoes, from Koybe!"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["edit_status"] == "published_minor_correction"
    with api.engine.connect() as connection:
        row = connection.execute(
            text("SELECT description,status FROM listings WHERE id=:id"),
            {"id": listing_id},
        ).one()
        events = connection.execute(
            text("""SELECT action FROM audit_events
                    WHERE resource_id=:id AND action='listing.minor_correction.published'"""),
            {"id": listing_id},
        ).scalars().all()
    assert tuple(row) == ("Fresh tomatoes, from Koybe!", "published")
    assert len(events) == 1


@pytest.mark.parametrize(
    "revocation_sql",
    [
        "UPDATE business_profiles SET verification_status='suspended',is_active=0 WHERE id='commerce-business'",
        "UPDATE business_memberships SET status='revoked' WHERE id='commerce-membership-owner'",
    ],
    ids=["business-verification-revoked", "seller-membership-revoked"],
)
def test_admin_edit_queue_and_approval_fail_closed_after_authority_revocation(
    commerce_api, monkeypatch, revocation_sql
):
    from app.dependencies import require_admin
    from app.models import Listing, ListingEdit
    from app.routers import listings as listings_router

    api = commerce_api
    # Each parameterized revocation scenario must begin from an independent,
    # known-good authority state so one case cannot make another pass falsely.
    with api.engine.begin() as connection:
        connection.execute(text("""
            UPDATE business_profiles
            SET verification_status='verified', is_active=1
            WHERE id='commerce-business'
        """))
        connection.execute(text("""
            UPDATE business_memberships
            SET status='active'
            WHERE id='commerce-membership-owner'
        """))
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    submitted = api.client.patch(
        f"/api/v1/listings/{listing_id}",
        json={"price_minor": 14500},
    )
    assert submitted.status_code == 200, submitted.text
    edit_id = submitted.json()["edit_id"]

    previous_override = app.dependency_overrides.get(require_admin)
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="commerce-owner")
    try:
        queue = api.client.get("/api/v1/admin/moderation/listing-edits")
        assert queue.status_code == 200, queue.text
        queued = [item for item in queue.json() if item["edit_id"] == edit_id]
        assert len(queued) == 1
        assert queued[0]["proposed_values"]["price_minor"] == 14500

        with api.engine.begin() as connection:
            connection.exec_driver_sql(revocation_sql)

        decision = api.client.post(
            f"/api/v1/admin/moderation/listing-edits/{edit_id}/decision",
            json={"decision": "approve", "note": "Must fail closed after revocation"},
        )
        assert decision.status_code == 409, decision.text
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(require_admin, None)
        else:
            app.dependency_overrides[require_admin] = previous_override

    with api.engine.connect() as connection:
        listing = connection.execute(
            text("SELECT price_minor,status FROM listings WHERE id=:id"),
            {"id": listing_id},
        ).one()
        edit_status = connection.execute(
            text("SELECT status FROM listing_edits WHERE id=:id"),
            {"id": edit_id},
        ).scalar_one()
    assert tuple(listing) == (10000, "published")
    assert edit_status == "pending_review"


def test_admin_edit_rejection_route_preserves_published_values_and_records_audit(
    commerce_api, monkeypatch
):
    from app.dependencies import require_admin
    from app.routers import listings as listings_router

    api = commerce_api
    listing_id = str(uuid4())
    _seed_published_listing_for_edit(api, listing_id)
    api.as_user("commerce-owner")
    monkeypatch.setattr(listings_router, "require_seller_business_listing_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(listings_router, "require_marketplace_listing_policy", lambda *args, **kwargs: None)

    submitted = api.client.patch(
        f"/api/v1/listings/{listing_id}",
        json={"price_minor": 15500},
    )
    assert submitted.status_code == 200, submitted.text
    edit_id = submitted.json()["edit_id"]

    previous_override = app.dependency_overrides.get(require_admin)
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id="commerce-owner")
    try:
        queue = api.client.get("/api/v1/admin/moderation/listing-edits")
        assert queue.status_code == 200, queue.text
        assert any(item["edit_id"] == edit_id for item in queue.json())
        rejected = api.client.post(
            f"/api/v1/admin/moderation/listing-edits/{edit_id}/decision",
            json={"decision": "reject", "note": "Synthetic evidence was insufficient"},
        )
        assert rejected.status_code == 200, rejected.text
        assert rejected.json()["status"] == "rejected"
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(require_admin, None)
        else:
            app.dependency_overrides[require_admin] = previous_override

    with api.engine.connect() as connection:
        listing = connection.execute(
            text("SELECT price_minor,status FROM listings WHERE id=:id"),
            {"id": listing_id},
        ).one()
        audit = connection.execute(
            text("""SELECT action FROM audit_events
                    WHERE resource_id=:id AND action='listing.edit.rejected'"""),
            {"id": listing_id},
        ).scalars().all()
    assert tuple(listing) == (10000, "published")
    assert len(audit) == 1
