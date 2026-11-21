from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import AuditEvent, Listing, Report, SellerProfile, User

router = APIRouter(prefix="/admin", tags=["admin"])


class ModerationDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


class ReportDecision(BaseModel):
    decision: Literal[
        "investigate", "resolve", "dismiss", "block_listing", "block_seller", "unblock_seller"
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
            "review_note": report.review_note, "target": target,
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
        previous = listing.status
        listing.status = "rejected"
        listing.moderation_note = payload.note or "Removed following an abuse report"
        listing.reviewed_by = admin.id
        listing.reviewed_at = now
        report.status = "resolved"
        metadata.update({"target_type": "listing", "target_id": listing.id, "previous_status": previous, "new_status": "rejected"})
        db.add(AuditEvent(
            actor_id=admin.id, action="listing.blocked_from_report", resource_type="listing",
            resource_id=listing.id, event_metadata={"report_id": report.id, "note": payload.note},
        ))
    elif action in {"block_seller", "unblock_seller"}:
        seller_id = report.seller_id
        if report.listing_id:
            listing = db.get(Listing, report.listing_id)
            seller_id = listing.seller_id if listing else None
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
