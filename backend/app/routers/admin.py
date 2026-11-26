from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import AuditEvent, Category, Listing, ListingEdit, Location, Report, SellerProfile, User
from app.governance_models import BusinessMembership, BusinessProfile

router = APIRouter(prefix="/admin", tags=["admin"])


class ModerationDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class ReportDecision(BaseModel):
    decision: Literal[
        "investigate", "resolve", "dismiss", "block_listing", "restore_listing", "block_seller", "unblock_seller"
    ]
    note: str | None = Field(default=None, max_length=2000)


def _queue_item(listing: Listing, seller: SellerProfile) -> dict[str, object]:
    return {
        "id": listing.id,
        "title": listing.title,
        "description": listing.description,
        "price_minor": listing.price_minor,
        "currency": listing.currency,
        "location": listing.location_label,
        "seller_id": seller.id,
        "seller_name": seller.public_name,
        "submitted_at": listing.created_at,
    }


@router.get("/moderation/queue")
def moderation_queue(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.execute(
        select(Listing, SellerProfile)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .where(Listing.status == "pending_review")
        .order_by(Listing.created_at.asc(), Listing.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [_queue_item(listing, seller) for listing, seller in rows]


@router.post("/moderation/{listing_id}/decision")
def decide_listing(
    listing_id: str,
    payload: ModerationDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.scalar(select(Listing).where(Listing.id == listing_id).with_for_update())
    if listing is None or listing.status != "pending_review":
        raise HTTPException(status_code=404, detail="Pending listing not found")

    previous_status = listing.status
    if payload.decision == "approve":
        seller = db.get(SellerProfile, listing.seller_id)
        business = db.get(BusinessProfile, seller.business_id) if seller and seller.business_id else None
        membership = db.scalar(select(BusinessMembership).where(
            BusinessMembership.business_id == business.id if business else False,
            BusinessMembership.user_id == seller.user_id if seller else False,
            BusinessMembership.status == "active",
            BusinessMembership.membership_role.in_(("owner", "administrator", "manager", "staff")),
            (BusinessMembership.expires_at.is_(None) | (BusinessMembership.expires_at > datetime.now(timezone.utc))),
        )) if business and seller else None
        if business is None or not business.is_active or business.verification_status != "verified" or membership is None:
            raise HTTPException(status_code=409, detail="Only listings owned by a verified active business with an active authorized membership can be published")
    next_status = "published" if payload.decision == "approve" else "rejected"
    listing.status = next_status
    listing.moderation_note = payload.note
    listing.reviewed_by = admin.id
    listing.reviewed_at = datetime.now(timezone.utc)
    db.add(AuditEvent(
        actor_id=admin.id,
        action="listing.moderation.approved" if payload.decision == "approve" else "listing.moderation.rejected",
        resource_type="listing",
        resource_id=listing.id,
        event_metadata={"previous_status": previous_status, "new_status": next_status, "note": payload.note},
    ))
    db.commit()
    return {"id": listing.id, "status": listing.status}


class ListingEditDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


@router.get("/moderation/listing-edits")
def listing_edit_queue(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.execute(
        select(ListingEdit, Listing, SellerProfile)
        .join(Listing, ListingEdit.listing_id == Listing.id)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .where(ListingEdit.status == "pending_review")
        .order_by(ListingEdit.created_at.asc(), ListingEdit.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [{
        "edit_id": edit.id,
        "listing_id": listing.id,
        "listing_status": listing.status,
        "seller_id": seller.id,
        "seller_name": seller.public_name,
        "current": {
            "title": listing.title,
            "description": listing.description,
            "category_id": listing.category_id,
            "price_minor": listing.price_minor,
            "location_label": listing.location_label,
            "location_id": listing.location_id,
            "attributes": listing.attributes or {},
        },
        "proposed_values": edit.proposed_values,
        "changed_fields": edit.changed_fields,
        "submitted_at": edit.created_at,
    } for edit, listing, seller in rows]


@router.post("/moderation/listing-edits/{edit_id}/decision")
def decide_listing_edit(
    edit_id: str,
    payload: ListingEditDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    edit = db.scalar(
        select(ListingEdit).where(ListingEdit.id == edit_id).with_for_update()
    )
    if edit is None or edit.status != "pending_review":
        raise HTTPException(status_code=404, detail="Pending listing edit not found")
    listing = db.scalar(
        select(Listing).where(Listing.id == edit.listing_id).with_for_update()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    if payload.decision == "approve":
        if listing.status != "published":
            raise HTTPException(status_code=409, detail="Only a currently published listing can accept an approved edit")
        seller = db.get(SellerProfile, listing.seller_id)
        business = db.get(BusinessProfile, seller.business_id) if seller and seller.business_id else None
        membership = db.scalar(select(BusinessMembership).where(
            BusinessMembership.business_id == business.id if business else False,
            BusinessMembership.user_id == seller.user_id if seller else False,
            BusinessMembership.status == "active",
            BusinessMembership.membership_role.in_(("owner", "administrator", "manager", "staff")),
            (BusinessMembership.expires_at.is_(None) | (BusinessMembership.expires_at > datetime.now(timezone.utc))),
        )) if business and seller else None
        seller_user = db.get(User, seller.user_id) if seller else None
        if (
            business is None or not business.is_active or business.verification_status != "verified"
            or membership is None or seller_user is None or not seller_user.is_active or seller_user.is_suspended
        ):
            raise HTTPException(status_code=409, detail="Only a verified active business with an active authorized seller can publish this edit")
        allowed = {"category_id", "title", "description", "attributes", "price_minor", "location_label", "location_id"}
        proposed = edit.proposed_values
        if not isinstance(proposed, dict) or not proposed or not set(proposed).issubset(allowed):
            raise HTTPException(status_code=409, detail="The proposed listing edit is invalid")
        if "category_id" in proposed or "attributes" in proposed:
            from app.routers.listings import _require_leaf_category, _validated_attributes

            category = db.get(Category, proposed.get("category_id", listing.category_id))
            if category is None or not category.is_active:
                raise HTTPException(status_code=409, detail="The proposed category is no longer active")
            try:
                _require_leaf_category(db, category)
                proposed["attributes"] = _validated_attributes(
                    category, proposed.get("attributes", listing.attributes or {})
                )
            except HTTPException as exc:
                raise HTTPException(
                    status_code=409,
                    detail="The proposed category or attributes are no longer valid",
                ) from exc
        if proposed.get("location_id") is not None:
            location = db.get(Location, proposed["location_id"])
            if location is None or not location.is_active:
                raise HTTPException(status_code=409, detail="The proposed location is no longer active")
        previous = {field: getattr(listing, field) for field in proposed}
        for field, value in proposed.items():
            setattr(listing, field, value)
        next_status = "approved"
        action = "listing.edit.approved"
        metadata = {"edit_id": edit.id, "changed_fields": edit.changed_fields, "previous_values": previous, "new_values": proposed, "note": payload.note}
    else:
        next_status = "rejected"
        action = "listing.edit.rejected"
        metadata = {"edit_id": edit.id, "changed_fields": edit.changed_fields, "note": payload.note}

    edit.status = next_status
    edit.pending_key = None
    edit.reviewed_by = admin.id
    edit.reviewed_at = datetime.now(timezone.utc)
    edit.moderation_note = payload.note
    db.add(AuditEvent(
        actor_id=admin.id,
        action=action,
        resource_type="listing",
        resource_id=listing.id,
        event_metadata=metadata,
    ))
    db.commit()
    return {"id": edit.id, "listing_id": listing.id, "status": edit.status}


@router.get("/reports")
def report_queue(
    report_status: Literal["pending", "in_review", "resolved", "dismissed"] | None = Query(default="pending", alias="status"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    statement = select(Report)
    if report_status is not None:
        statement = statement.where(Report.status == report_status)
    rows = db.scalars(
        statement.order_by(Report.created_at.asc(), Report.id.asc()).offset(offset).limit(limit)
    ).all()
    result = []
    for report in rows:
        target = None
        if report.listing_id:
            listing = db.get(Listing, report.listing_id)
            if listing:
                seller = db.get(SellerProfile, listing.seller_id)
                target = {
                    "type": "listing", "id": listing.id, "title": listing.title,
                    "status": listing.status, "seller_id": seller.id if seller else None,
                    "seller_name": seller.public_name if seller else None,
                }
        elif report.seller_id:
            seller = db.get(SellerProfile, report.seller_id)
            if seller:
                user = db.get(User, seller.user_id)
                target = {
                    "type": "seller", "id": seller.id, "seller_name": seller.public_name,
                    "suspended": bool(user and user.is_suspended),
                }
        result.append({
            "id": report.id, "reporter_user_id": report.reporter_user_id,
            "reason": report.reason, "description": report.description,
            "evidence": report.evidence, "status": report.status,
            "review_note": report.review_note, "previous_target_status": report.previous_target_status, "target": target,
            "created_at": report.created_at, "reviewed_at": report.reviewed_at,
        })
    return result


@router.post("/reports/{report_id}/decision")
def decide_report(
    report_id: str,
    payload: ReportDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    report = db.scalar(select(Report).where(Report.id == report_id).with_for_update())
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status in {"resolved", "dismissed"} and payload.decision not in {"unblock_seller"}:
        raise HTTPException(status_code=409, detail="Report is already closed")

    if payload.decision in {"resolve", "dismiss"} and report.seller_id:
        seller = db.get(SellerProfile, report.seller_id)
        seller_user = db.get(User, seller.user_id) if seller else None
        if seller_user is not None and seller_user.is_suspended:
            raise HTTPException(status_code=409, detail="Reinstate the seller before closing this report")
    if payload.decision == "dismiss" and report.previous_target_status is not None:
        raise HTTPException(status_code=409, detail="Restore the listing before dismissing this report")

    now = datetime.now(timezone.utc)
    action = payload.decision
    resource_type = "report"
    resource_id = report.id
    metadata: dict[str, object] = {"decision": action, "note": payload.note}

    if action == "investigate":
        report.status = "in_review"
    elif action == "resolve":
        report.status = "resolved"
    elif action == "dismiss":
        report.status = "dismissed"
    elif action == "block_listing":
        if not report.listing_id:
            raise HTTPException(status_code=422, detail="This report does not target a listing")
        listing = db.scalar(select(Listing).where(Listing.id == report.listing_id).with_for_update())
        if listing is None:
            raise HTTPException(status_code=404, detail="Reported listing no longer exists")
        if listing.status not in {"published", "pending_review"}:
            raise HTTPException(status_code=409, detail="Only visible or pending listings can be blocked from a report")
        previous = listing.status
        report.previous_target_status = previous
        listing.status = "rejected"
        listing.moderation_note = payload.note or "Removed following an abuse report"
        listing.reviewed_by = admin.id
        listing.reviewed_at = now
        report.status = "in_review"
        metadata.update({"target_type": "listing", "target_id": listing.id, "previous_status": previous, "new_status": "rejected"})
        db.add(AuditEvent(
            actor_id=admin.id, action="listing.blocked_from_report", resource_type="listing",
            resource_id=listing.id, event_metadata={"report_id": report.id, "previous_status": previous, "note": payload.note},
        ))
    elif action == "restore_listing":
        if not report.listing_id or not report.previous_target_status:
            raise HTTPException(status_code=422, detail="This report has no reversible listing block")
        listing = db.scalar(select(Listing).where(Listing.id == report.listing_id).with_for_update())
        if listing is None:
            raise HTTPException(status_code=404, detail="Reported listing no longer exists")
        if listing.status != "rejected":
            raise HTTPException(status_code=409, detail="Reported listing is not currently blocked")
        previous = report.previous_target_status
        listing.status = previous
        listing.moderation_note = payload.note or "Restored after report review"
        listing.reviewed_by = admin.id
        listing.reviewed_at = now
        report.previous_target_status = None
        report.status = "in_review"
        metadata.update({"target_type": "listing", "target_id": listing.id, "previous_status": "rejected", "new_status": previous})
        db.add(AuditEvent(
            actor_id=admin.id, action="listing.restored_from_report", resource_type="listing",
            resource_id=listing.id, event_metadata={"report_id": report.id, "restored_status": previous, "note": payload.note},
        ))
    elif action in {"block_seller", "unblock_seller"}:
        seller_id = report.seller_id
        if not seller_id:
            raise HTTPException(status_code=404, detail="Reported seller no longer exists")
        seller = db.get(SellerProfile, seller_id)
        user = db.scalar(select(User).where(User.id == seller.user_id).with_for_update()) if seller else None
        if user is None:
            raise HTTPException(status_code=404, detail="Reported seller no longer exists")
        if action == "unblock_seller" and not user.is_suspended:
            raise HTTPException(status_code=409, detail="Seller account is not suspended")
        if action == "block_seller" and not user.is_suspended:
            user.auth_version += 1
        user.is_suspended = action == "block_seller"
        report.status = "in_review"
        metadata.update({"target_type": "seller_account", "seller_id": seller.id, "suspended": user.is_suspended})
        db.add(AuditEvent(
            actor_id=admin.id, action="seller.account_suspended" if user.is_suspended else "seller.account_reinstated",
            resource_type="user", resource_id=user.id,
            event_metadata={"report_id": report.id, "note": payload.note},
        ))

    report.reviewed_by = admin.id
    report.review_note = payload.note
    report.reviewed_at = now
    db.add(AuditEvent(
        actor_id=admin.id, action=f"report.{action}", resource_type=resource_type,
        resource_id=resource_id, event_metadata=metadata,
    ))
    db.commit()
    return {"id": report.id, "status": report.status, "decision": action}


@router.get("/audit-events")
def audit_events(
    resource_type: str | None = Query(default=None, min_length=1, max_length=80),
    resource_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    statement = select(AuditEvent)
    if resource_type:
        statement = statement.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        statement = statement.where(AuditEvent.resource_id == resource_id)
    events = db.scalars(
        statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit)
    ).all()
    return [{
        "id": event.id, "actor_id": event.actor_id, "action": event.action,
        "resource_type": event.resource_type, "resource_id": event.resource_id,
        "metadata": event.event_metadata, "created_at": event.created_at,
    } for event in events]
