from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import AuditEvent, Listing, SellerProfile, User

router = APIRouter(prefix="/admin", tags=["admin"])


class ModerationDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1000)


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
    listing = db.scalar(
        select(Listing).where(Listing.id == listing_id).with_for_update()
    )
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
        action=f"listing.moderation.{payload.decision}d",
        resource_type="listing",
        resource_id=listing.id,
        event_metadata={
            "previous_status": previous_status,
            "new_status": next_status,
            "note": payload.note,
        },
    ))
    # The listing transition and its audit event commit atomically.
    db.commit()
    return {"id": listing.id, "status": listing.status}


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
        statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "metadata": event.event_metadata,
            "created_at": event.created_at,
        }
        for event in events
    ]
