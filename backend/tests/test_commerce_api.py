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
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
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
    assert isinstance(placed_event, dict)
    assert placed_event["settlement_method"] == "direct_cash"

    api.as_user("commerce-viewer")
    visible = api.client.get(f"/api/v1/commerce/orders/{order_id}")
    assert visible.status_code == 200, visible.text
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
