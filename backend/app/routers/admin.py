from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import Listing, SellerProfile, User

router = APIRouter(prefix="/admin/moderation", tags=["admin-moderation"])


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


@router.get("/queue")
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


@router.post("/{listing_id}/decision")
def decide_listing(
    listing_id: str,
    payload: ModerationDecision,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status != "pending_review":
        raise HTTPException(status_code=404, detail="Pending listing not found")
    listing.status = "published" if payload.decision == "approve" else "rejected"
    listing.moderation_note = payload.note
    listing.reviewed_by = admin.id
    listing.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": listing.id, "status": listing.status}
