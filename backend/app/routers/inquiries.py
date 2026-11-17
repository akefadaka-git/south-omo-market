from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Inquiry, Listing, SellerProfile, User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/inquiries")


class InquiryCreate(BaseModel):
    listing_id: str
    message: str = Field(min_length=1, max_length=2000)


class InquiryStatusUpdate(BaseModel):
    status: Literal["open", "read", "closed"]


def _inquiry_payload(
    inquiry: Inquiry, listing: Listing, *, include_buyer_contact: bool
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": inquiry.id,
        "listing_id": listing.id,
        "listing_title": listing.title,
        "message": inquiry.message,
        "status": inquiry.status,
        "created_at": inquiry.created_at,
        "read_at": inquiry.read_at,
        "closed_at": inquiry.closed_at,
    }
    if include_buyer_contact:
        result.update({
            "buyer_name": inquiry.buyer_name,
            "buyer_contact": inquiry.contact_value,
            "buyer_user_id": inquiry.buyer_user_id,
        })
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def create_inquiry(
    request: Request,
    response: Response,
    payload: InquiryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.get(Listing, payload.listing_id)
    if listing is None or listing.status != "published":
        raise HTTPException(status_code=404, detail="Listing not found")
    seller = db.get(SellerProfile, listing.seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if seller.user_id == user.id:
        raise HTTPException(status_code=409, detail="You cannot inquire about your own listing")

    inquiry = Inquiry(
        listing_id=listing.id,
        buyer_user_id=user.id,
        buyer_name=user.display_name,
        contact_value=user.phone_number,
        message=payload.message,
        status="open",
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return {"id": inquiry.id, "status": inquiry.status}


@router.get("/inbox")
def seller_inbox(
    status_filter: Literal["open", "read", "closed"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=403, detail="Seller profile required")
    statement = (
        select(Inquiry, Listing)
        .join(Listing, Inquiry.listing_id == Listing.id)
        .where(Listing.seller_id == seller.id)
    )
    if status_filter:
        statement = statement.where(Inquiry.status == status_filter)
    rows = db.execute(
        statement.order_by(Inquiry.created_at.desc(), Inquiry.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        _inquiry_payload(inquiry, listing, include_buyer_contact=True)
        for inquiry, listing in rows
    ]


@router.get("/mine")
def my_inquiries(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.execute(
        select(Inquiry, Listing)
        .join(Listing, Inquiry.listing_id == Listing.id)
        .where(Inquiry.buyer_user_id == user.id)
        .order_by(Inquiry.created_at.desc(), Inquiry.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        _inquiry_payload(inquiry, listing, include_buyer_contact=False)
        for inquiry, listing in rows
    ]


@router.patch("/{inquiry_id}/status")
def update_inquiry_status(
    inquiry_id: str,
    payload: InquiryStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=403, detail="Seller profile required")
    inquiry = db.scalar(
        select(Inquiry)
        .join(Listing, Inquiry.listing_id == Listing.id)
        .where(Inquiry.id == inquiry_id, Listing.seller_id == seller.id)
        .with_for_update()
    )
    if inquiry is None:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    now = datetime.now(timezone.utc)
    inquiry.status = payload.status
    if payload.status != "open" and inquiry.read_at is None:
        inquiry.read_at = now
    if payload.status == "closed":
        inquiry.closed_at = now
    else:
        inquiry.closed_at = None
    db.commit()
    return {"id": inquiry.id, "status": inquiry.status}
