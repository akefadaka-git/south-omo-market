"""Business-scoped catalog, inventory, agreements, carts and order lifecycle.

Payment processing is deliberately out of scope: orders record direct-cash settlement
intent only. No gateway, escrow, wallet or automatic money movement is implemented.
"""
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import JSON, bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.governance import require_business_permission
from app.models import User

router = APIRouter(prefix="/commerce")


class CatalogItemCreate(BaseModel):
    category_id: str = Field(min_length=1, max_length=36)
    sku: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=5000)
    unit_price_minor: int = Field(ge=0)
    unit: str = Field(default="item", min_length=1, max_length=32)
    currency: str = "ETB"


class InventoryAdjustment(BaseModel):
    quantity_delta: int
    movement_type: str = "adjustment"
    reason: str = Field(min_length=3, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=120)


class AgreementCreate(BaseModel):
    counterparty_business_id: str | None = None
    counterparty_user_id: str | None = None
    agreement_type: str = "trade_terms"
    agreement_code: str = Field(min_length=2, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    terms_text: str = Field(min_length=10, max_length=20000)


class CartItemPut(BaseModel):
    catalog_item_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(gt=0, le=100000)


def _event(db: Session, order_id: str, actor_id: str | None, event_type: str, metadata: dict | None = None):
    db.execute(text("""
        INSERT INTO commerce_order_events (id,order_id,actor_id,event_type,event_metadata)
        VALUES (:id,:order_id,:actor,:event,:metadata)
    """).bindparams(bindparam("metadata", type_=JSON)),
        {"id": str(uuid4()), "order_id": order_id, "actor": actor_id,
         "event": event_type, "metadata": metadata or {}})


def _inventory_movement(
    db: Session, *, business_id: str, item_id: str, movement_type: str,
    quantity_delta: int, reference_id: str, idempotency_key: str,
    reason: str, actor_id: str | None,
) -> None:
    db.execute(text("""
        INSERT INTO inventory_movements
            (id,business_id,catalog_item_id,movement_type,quantity_delta,
             reference_type,reference_id,idempotency_key,reason,actor_id)
        VALUES (:id,:business,:item,:kind,:delta,'commerce_order',:reference,
                :key,:reason,:actor)
    """), {
        "id": str(uuid4()), "business": business_id, "item": item_id,
        "kind": movement_type, "delta": quantity_delta, "reference": reference_id,
        "key": idempotency_key, "reason": reason, "actor": actor_id,
    })

@router.post("/businesses/{business_id}/catalog", status_code=201)
def create_catalog_item(
    business_id: str, payload: CatalogItemCreate,
    user: User = Depends(require_business_permission("commerce.catalog.manage")),
    db: Session = Depends(get_db),
):
    if payload.currency != "ETB":
        raise HTTPException(422, "Only ETB is supported in commerce v1")
    category = db.execute(text("""
        SELECT id FROM categories WHERE id=:id AND is_active=TRUE
    """), {"id": payload.category_id}).scalar_one_or_none()
    if category is None:
        raise HTTPException(422, "An active category is required")
    item_id = str(uuid4())
    try:
        db.execute(text("""
            INSERT INTO commerce_catalog_items
            (id,business_id,category_id,sku,title,description,currency,unit_price_minor,unit,status,created_by)
            VALUES (:id,:business,:category,:sku,:title,:description,'ETB',:price,:unit,'active',:actor)
        """), {"id": item_id, "business": business_id, "category": payload.category_id,
               "sku": payload.sku.strip(), "title": payload.title.strip(),
               "description": payload.description, "price": payload.unit_price_minor,
               "unit": payload.unit, "actor": user.id})
        db.execute(text("""
            INSERT INTO inventory_balances (id,business_id,catalog_item_id,quantity_on_hand,quantity_reserved)
            VALUES (:id,:business,:item,0,0)
        """), {"id": str(uuid4()), "business": business_id, "item": item_id})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "SKU already exists for this business or catalog data is invalid") from exc
    return {"id": item_id, "business_id": business_id, "status": "active"}


@router.get("/businesses/{business_id}/catalog")
def list_catalog_items(business_id: str, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT c.id,c.business_id,c.category_id,c.sku,c.title,c.description,c.currency,
               c.unit_price_minor,c.unit,c.status,
               (b.quantity_on_hand-b.quantity_reserved) AS available_quantity
        FROM commerce_catalog_items c
        JOIN inventory_balances b ON b.catalog_item_id=c.id
        JOIN business_profiles bp ON bp.id=c.business_id
        WHERE c.business_id=:business AND c.status='active'
          AND bp.is_active=TRUE AND bp.verification_status='verified'
        ORDER BY c.title,c.sku
    """), {"business": business_id}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/businesses/{business_id}/catalog/{item_id}/inventory", status_code=201)
def adjust_inventory(
    business_id: str, item_id: str, payload: InventoryAdjustment,
    user: User = Depends(require_business_permission("commerce.catalog.manage")),
    db: Session = Depends(get_db),
):
    if payload.movement_type not in {"receipt", "adjustment"} or payload.quantity_delta == 0:
        raise HTTPException(422, "Only non-zero receipt or adjustment movements are supported")
    balance_exists = db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM inventory_balances
        WHERE business_id=:business AND catalog_item_id=:item)
    """), {"business": business_id, "item": item_id}).scalar_one()
    if not balance_exists:
        raise HTTPException(404, "Business inventory item not found")
    if db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM inventory_movements
        WHERE business_id=:business AND idempotency_key=:key)
    """), {"business": business_id, "key": payload.idempotency_key}).scalar_one():
        existing = db.execute(text("""
            SELECT id,catalog_item_id,quantity_delta,movement_type FROM inventory_movements
            WHERE business_id=:business AND idempotency_key=:key
        """), {"business": business_id, "key": payload.idempotency_key}).mappings().one()
        if existing["catalog_item_id"] != item_id or existing["quantity_delta"] != payload.quantity_delta or existing["movement_type"] != payload.movement_type:
            raise HTTPException(409, "Idempotency key was already used for a different movement")
        return {"movement_id": existing["id"], "replayed": True}
    movement_id = str(uuid4())
    try:
        changed = db.execute(text("""
            UPDATE inventory_balances
            SET quantity_on_hand=quantity_on_hand+:delta,updated_at=CURRENT_TIMESTAMP
            WHERE business_id=:business AND catalog_item_id=:item
              AND quantity_on_hand+:delta>=quantity_reserved
        """), {"delta": payload.quantity_delta, "business": business_id, "item": item_id})
        if changed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Adjustment would consume reserved stock or inventory changed")
        db.execute(text("""
            INSERT INTO inventory_movements
            (id,business_id,catalog_item_id,movement_type,quantity_delta,idempotency_key,reason,actor_id)
            VALUES (:id,:business,:item,:kind,:delta,:key,:reason,:actor)
        """), {"id": movement_id, "business": business_id, "item": item_id,
               "kind": payload.movement_type, "delta": payload.quantity_delta,
               "key": payload.idempotency_key, "reason": payload.reason, "actor": user.id})
        new_on_hand = db.execute(text("""
            SELECT quantity_on_hand FROM inventory_balances
            WHERE business_id=:business AND catalog_item_id=:item
        """), {"business": business_id, "item": item_id}).scalar_one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.execute(text("""
            SELECT id,catalog_item_id,quantity_delta,movement_type FROM inventory_movements
            WHERE business_id=:business AND idempotency_key=:key
        """), {"business": business_id, "key": payload.idempotency_key}).mappings().first()
        if existing and existing["catalog_item_id"] == item_id and existing["quantity_delta"] == payload.quantity_delta and existing["movement_type"] == payload.movement_type:
            return {"movement_id": existing["id"], "replayed": True}
        raise HTTPException(409, "Inventory movement conflicts with a concurrent update") from exc
    return {"movement_id": movement_id, "quantity_on_hand": new_on_hand, "replayed": False}


@router.post("/businesses/{business_id}/agreements", status_code=201)
def create_agreement(
    business_id: str, payload: AgreementCreate,
    user: User = Depends(require_business_permission("commerce.catalog.manage")),
    db: Session = Depends(get_db),
):
    if bool(payload.counterparty_business_id) == bool(payload.counterparty_user_id):
        raise HTTPException(422, "Specify exactly one counterparty")
    if payload.agreement_type not in {"seller_terms", "buyer_terms", "trade_terms", "service_terms"}:
        raise HTTPException(422, "Unsupported agreement type")
    if payload.counterparty_business_id == business_id:
        raise HTTPException(422, "A business cannot be its own counterparty")
    if payload.counterparty_business_id and db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM business_profiles WHERE id=:id AND is_active=TRUE)
    """), {"id": payload.counterparty_business_id}).scalar_one() is False:
        raise HTTPException(404, "Counterparty business not found")
    if payload.counterparty_user_id and db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM users WHERE id=:id AND is_active=TRUE AND is_suspended=FALSE)
    """), {"id": payload.counterparty_user_id}).scalar_one() is False:
        raise HTTPException(404, "Counterparty account not found")
    agreement_id = str(uuid4())
    digest = sha256(payload.terms_text.encode("utf-8")).hexdigest()
    db.execute(text("""
        INSERT INTO commerce_agreements
        (id,business_id,counterparty_business_id,counterparty_user_id,agreement_type,
         agreement_code,version,terms_text,terms_sha256,status,created_by)
        VALUES (:id,:business,:counterparty_business,:counterparty_user,:kind,
                :code,:version,:terms,:digest,'offered',:actor)
    """), {"id": agreement_id, "business": business_id,
           "counterparty_business": payload.counterparty_business_id,
           "counterparty_user": payload.counterparty_user_id, "kind": payload.agreement_type,
           "code": payload.agreement_code, "version": payload.version,
           "terms": payload.terms_text, "digest": digest, "actor": user.id})
    db.execute(text("""
        INSERT INTO commerce_agreement_events (id,agreement_id,actor_id,event_type,event_metadata)
        VALUES (:id,:agreement,:actor,'offered',:metadata)
    """).bindparams(bindparam("metadata", type_=JSON)),
        {"id": str(uuid4()), "agreement": agreement_id, "actor": user.id,
         "metadata": {"terms_sha256": digest}})
    db.commit()
    return {"id": agreement_id, "status": "offered", "terms_sha256": digest}


@router.post("/agreements/{agreement_id}/decision")
def decide_agreement(
    agreement_id: str, decision: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if decision not in {"accepted", "rejected"}:
        raise HTTPException(422, "Decision must be accepted or rejected")
    row = db.execute(text("""
        SELECT id,business_id,counterparty_business_id,counterparty_user_id,status
        FROM commerce_agreements WHERE id=:id
    """), {"id": agreement_id}).mappings().first()
    if row is None:
        raise HTTPException(404, "Agreement not found")
    is_counterparty = row["counterparty_user_id"] == user.id
    if row["counterparty_business_id"]:
        is_counterparty = db.execute(text("""
            SELECT EXISTS(SELECT 1 FROM business_memberships bm
            JOIN business_profiles bp ON bp.id=bm.business_id
            WHERE bm.business_id=:business AND bm.user_id=:user AND bm.status='active'
              AND (bm.expires_at IS NULL OR bm.expires_at>CURRENT_TIMESTAMP)
              AND bm.membership_role IN ('owner','administrator')
              AND bp.is_active=TRUE AND bp.verification_status='verified')
        """), {"business": row["counterparty_business_id"], "user": user.id}).scalar_one()
    if not is_counterparty:
        raise HTTPException(403, "Only the designated counterparty may decide this agreement")
    if row["status"] != "offered":
        raise HTTPException(409, "Agreement is not awaiting a counterparty decision")
    changed = db.execute(text("""
        UPDATE commerce_agreements SET status=:status,updated_at=CURRENT_TIMESTAMP
        WHERE id=:id AND status='offered'
    """), {"status": decision, "id": agreement_id})
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Agreement was decided concurrently; reload before retrying")
    db.execute(text("""
        INSERT INTO commerce_agreement_events (id,agreement_id,actor_id,event_type,event_metadata)
        VALUES (:id,:agreement,:actor,:event,'{}')
    """), {"id": str(uuid4()), "agreement": agreement_id, "actor": user.id, "event": decision})
    db.commit()
    return {"id": agreement_id, "status": decision}


@router.post("/businesses/{business_id}/carts", status_code=201)
def create_cart(business_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.execute(text("""
        SELECT EXISTS(SELECT 1 FROM business_profiles
        WHERE id=:id AND is_active=TRUE AND verification_status='verified')
    """), {"id": business_id}).scalar_one() is False:
        raise HTTPException(404, "Verified business not found")
    cart_id = str(uuid4())
    try:
        db.execute(text("""
            INSERT INTO commerce_carts (id,buyer_user_id,business_id,status)
            VALUES (:id,:buyer,:business,'active')
        """), {"id": cart_id, "buyer": user.id, "business": business_id})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        row = db.execute(text("""
            SELECT id FROM commerce_carts WHERE buyer_user_id=:buyer
              AND business_id=:business AND status='active'
        """), {"buyer": user.id, "business": business_id}).mappings().first()
        if row:
            return {"id": row["id"], "reused": True}
        raise HTTPException(409, "Unable to create cart") from exc
    return {"id": cart_id, "reused": False}


@router.put("/carts/{cart_id}/items")
def put_cart_item(cart_id: str, payload: CartItemPut,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = db.execute(text("""
        SELECT id,business_id FROM commerce_carts
        WHERE id=:id AND buyer_user_id=:buyer AND status='active'
    """), {"id": cart_id, "buyer": user.id}).mappings().first()
    if cart is None:
        raise HTTPException(404, "Active cart not found")
    item = db.execute(text("""
        SELECT c.id,c.unit_price_minor,c.status,b.quantity_on_hand,b.quantity_reserved
        FROM commerce_catalog_items c JOIN inventory_balances b ON b.catalog_item_id=c.id
        WHERE c.id=:item AND c.business_id=:business
    """), {"item": payload.catalog_item_id, "business": cart["business_id"]}).mappings().first()
    if item is None or item["status"] != "active":
        raise HTTPException(404, "Active catalog item not found in this business")
    if payload.quantity > item["quantity_on_hand"] - item["quantity_reserved"]:
        raise HTTPException(409, "Requested quantity exceeds available stock")
    db.execute(text("""
        INSERT INTO commerce_cart_items (id,cart_id,catalog_item_id,quantity)
        VALUES (:id,:cart,:item,:quantity)
        ON CONFLICT (cart_id,catalog_item_id) DO UPDATE SET quantity=EXCLUDED.quantity,
            updated_at=CURRENT_TIMESTAMP
    """), {"id": str(uuid4()), "cart": cart_id, "item": payload.catalog_item_id,
           "quantity": payload.quantity})
    db.commit()
    return {"cart_id": cart_id, "catalog_item_id": payload.catalog_item_id, "quantity": payload.quantity}


@router.get("/carts/{cart_id}")
def get_cart(cart_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart = db.execute(text("""
        SELECT id,business_id,status FROM commerce_carts
        WHERE id=:id AND buyer_user_id=:buyer
    """), {"id": cart_id, "buyer": user.id}).mappings().first()
    if cart is None:
        raise HTTPException(404, "Cart not found")
    rows = db.execute(text("""
        SELECT ci.catalog_item_id,ci.quantity,c.sku,c.title,c.unit_price_minor,
               (ci.quantity*c.unit_price_minor) AS line_total_minor
        FROM commerce_cart_items ci JOIN commerce_catalog_items c ON c.id=ci.catalog_item_id
        WHERE ci.cart_id=:cart ORDER BY c.title
    """), {"cart": cart_id}).mappings().all()
    return {"cart": dict(cart), "items": [dict(row) for row in rows]}


@router.post("/carts/{cart_id}/checkout", status_code=201)
def checkout_cart(cart_id: str, idempotency_key: str = Query(min_length=8, max_length=120),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("""
        SELECT id,order_number,status FROM commerce_orders
        WHERE buyer_user_id=:buyer AND idempotency_key=:key
    """), {"buyer": user.id, "key": idempotency_key}).mappings().first()
    if existing:
        return {"order_id": existing["id"], "order_number": existing["order_number"],
                "status": existing["status"], "replayed": True}
    cart = db.execute(text("""
        SELECT id,business_id FROM commerce_carts
        WHERE id=:id AND buyer_user_id=:buyer AND status='active'
    """), {"id": cart_id, "buyer": user.id}).mappings().first()
    if cart is None:
        raise HTTPException(404, "Active cart not found")
    claimed = db.execute(text("""
        UPDATE commerce_carts SET status='converted',updated_at=CURRENT_TIMESTAMP
        WHERE id=:id AND buyer_user_id=:buyer AND status='active'
    """), {"id": cart_id, "buyer": user.id})
    if claimed.rowcount != 1:
        db.rollback()
        existing = db.execute(text("""
            SELECT id,order_number,status FROM commerce_orders
            WHERE buyer_user_id=:buyer AND idempotency_key=:key
        """), {"buyer": user.id, "key": idempotency_key}).mappings().first()
        if existing:
            return {"order_id": existing["id"], "order_number": existing["order_number"],
                    "status": existing["status"], "replayed": True}
        raise HTTPException(409, "Cart is already being checked out or has been converted")
    items = db.execute(text("""
        SELECT ci.catalog_item_id,ci.quantity,c.sku,c.title,c.unit_price_minor,
               b.quantity_on_hand,b.quantity_reserved
        FROM commerce_cart_items ci
        JOIN commerce_catalog_items c ON c.id=ci.catalog_item_id
        JOIN inventory_balances b ON b.catalog_item_id=c.id
        WHERE ci.cart_id=:cart AND c.business_id=:business AND c.status='active'
    """), {"cart": cart_id, "business": cart["business_id"]}).mappings().all()
    if not items:
        raise HTTPException(409, "Cart is empty")
    for item in items:
        if item["quantity"] > item["quantity_on_hand"] - item["quantity_reserved"]:
            raise HTTPException(409, "Cart contains an item with insufficient stock")
    subtotal = sum(item["quantity"] * item["unit_price_minor"] for item in items)
    order_id, order_number = str(uuid4()), "SOM-" + uuid4().hex[:12].upper()
    try:
        db.execute(text("""
            INSERT INTO commerce_orders
            (id,order_number,buyer_user_id,business_id,status,currency,subtotal_minor,total_minor,
             settlement_method,idempotency_key)
            VALUES (:id,:number,:buyer,:business,'placed','ETB',:subtotal,:subtotal,'direct_cash',:key)
        """), {"id": order_id, "number": order_number, "buyer": user.id,
               "business": cart["business_id"], "subtotal": subtotal, "key": idempotency_key})
        for item in items:
            reserved = db.execute(text("""
                UPDATE inventory_balances SET quantity_reserved=quantity_reserved+:quantity,
                    updated_at=CURRENT_TIMESTAMP
                WHERE catalog_item_id=:item AND quantity_on_hand-quantity_reserved>=:quantity
            """), {"quantity": item["quantity"], "item": item["catalog_item_id"]})
            if reserved.rowcount != 1:
                db.rollback()
                raise HTTPException(409, "Stock changed during checkout; retry with a refreshed cart")
            db.execute(text("""
                INSERT INTO commerce_order_items
                (id,order_id,catalog_item_id,sku_snapshot,title_snapshot,unit_price_minor,quantity,line_total_minor)
                VALUES (:id,:order,:item,:sku,:title,:price,:quantity,:total)
            """), {"id": str(uuid4()), "order": order_id, "item": item["catalog_item_id"],
                   "sku": item["sku"], "title": item["title"], "price": item["unit_price_minor"],
                   "quantity": item["quantity"], "total": item["quantity"] * item["unit_price_minor"]})
            _inventory_movement(
                db, business_id=cart["business_id"], item_id=item["catalog_item_id"],
                movement_type="reservation", quantity_delta=item["quantity"],
                reference_id=order_id,
                idempotency_key=f"order:{order_id}:reservation:{item['catalog_item_id']}",
                reason="Order placed; stock reserved", actor_id=user.id,
            )
        _event(db, order_id, user.id, "placed", {"settlement_method": "direct_cash"})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Order conflicts with stock or idempotency constraints") from exc
    return {"order_id": order_id, "order_number": order_number, "status": "placed",
            "currency": "ETB", "total_minor": subtotal, "settlement_method": "direct_cash",
            "replayed": False}


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.execute(text("""
        SELECT id,order_number,buyer_user_id,business_id,status,currency,subtotal_minor,total_minor,
               settlement_method,buyer_note,seller_note,created_at,updated_at
        FROM commerce_orders WHERE id=:id
    """), {"id": order_id}).mappings().first()
    if order is None:
        raise HTTPException(404, "Order not found")
    is_buyer = order["buyer_user_id"] == user.id
    is_member = False
    if not is_buyer:
        is_member = db.execute(text("""
            SELECT EXISTS(
                SELECT 1 FROM business_memberships bm
                JOIN business_profiles bp ON bp.id=bm.business_id
                JOIN business_role_permissions rp ON rp.membership_role=bm.membership_role
                WHERE bm.business_id=:business AND bm.user_id=:user
                  AND bm.status='active'
                  AND (bm.expires_at IS NULL OR bm.expires_at>CURRENT_TIMESTAMP)
                  AND bp.is_active=TRUE AND bp.verification_status='verified'
                  AND rp.permission_code IN ('commerce.order.read','commerce.order.manage')
            )
        """), {"business": order["business_id"], "user": user.id}).scalar_one()
    if not is_buyer and not is_member:
        raise HTTPException(404, "Order not found")
    items = db.execute(text("""
        SELECT sku_snapshot,title_snapshot,unit_price_minor,quantity,line_total_minor
        FROM commerce_order_items WHERE order_id=:id ORDER BY title_snapshot
    """), {"id": order_id}).mappings().all()
    return {"order": dict(order), "items": [dict(item) for item in items]}


@router.post("/businesses/{business_id}/orders/{order_id}/status")
def update_order_status(
    business_id: str, order_id: str, new_status: str,
    user: User = Depends(require_business_permission("commerce.order.manage")),
    db: Session = Depends(get_db),
):
    transitions = {
        "placed": {"accepted", "rejected", "cancelled"},
        "accepted": {"ready", "cancelled"},
        "ready": {"fulfilled", "cancelled"},
    }
    row = db.execute(text("""
        SELECT id,status FROM commerce_orders WHERE id=:id AND business_id=:business
    """), {"id": order_id, "business": business_id}).mappings().first()
    if row is None:
        raise HTTPException(404, "Order not found")
    previous_status = row["status"]
    if new_status not in transitions.get(previous_status, set()):
        raise HTTPException(409, "Invalid order status transition")
    changed = db.execute(text("""
        UPDATE commerce_orders SET status=:new_status,updated_at=CURRENT_TIMESTAMP
        WHERE id=:id AND business_id=:business AND status=:old_status
    """), {"new_status": new_status, "id": order_id,
           "business": business_id, "old_status": previous_status})
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Order status changed concurrently; reload before retrying")
    items = db.execute(text("""
        SELECT catalog_item_id,quantity FROM commerce_order_items WHERE order_id=:id
    """), {"id": order_id}).mappings().all()
    if new_status in {"rejected", "cancelled", "fulfilled"}:
        for item in items:
            quantity = item["quantity"]
            if new_status in {"rejected", "cancelled"}:
                result = db.execute(text("""
                    UPDATE inventory_balances
                    SET quantity_reserved=quantity_reserved-:quantity,updated_at=CURRENT_TIMESTAMP
                    WHERE business_id=:business AND catalog_item_id=:item
                      AND quantity_reserved>=:quantity
                """), {"quantity": quantity, "business": business_id,
                       "item": item["catalog_item_id"]})
                movement_type, delta, reason, suffix = "release", -quantity, "Order reservation released", "release"
            else:
                result = db.execute(text("""
                    UPDATE inventory_balances
                    SET quantity_on_hand=quantity_on_hand-:quantity,
                        quantity_reserved=quantity_reserved-:quantity,updated_at=CURRENT_TIMESTAMP
                    WHERE business_id=:business AND catalog_item_id=:item
                      AND quantity_reserved>=:quantity AND quantity_on_hand>=:quantity
                """), {"quantity": quantity, "business": business_id,
                       "item": item["catalog_item_id"]})
                movement_type, delta, reason, suffix = "fulfillment", -quantity, "Order fulfilled; stock consumed", "fulfillment"
            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(409, "Reserved stock is inconsistent; transition blocked")
            _inventory_movement(
                db, business_id=business_id, item_id=item["catalog_item_id"],
                movement_type=movement_type, quantity_delta=delta, reference_id=order_id,
                idempotency_key=f"order:{order_id}:{suffix}:{item['catalog_item_id']}",
                reason=reason, actor_id=user.id,
            )
    _event(db, order_id, user.id, new_status)
    db.commit()
    return {"order_id": order_id, "status": new_status}
