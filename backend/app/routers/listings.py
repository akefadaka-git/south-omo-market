from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Listing

router = APIRouter(prefix="/listings")

@router.get("")
def list_public_listings(limit: int = Query(default=20, ge=1, le=100),
                         db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(Listing).where(Listing.status == "published")
                      .order_by(Listing.created_at.desc()).limit(limit)).all()
    return [{"id": row.id, "title": row.title, "price_minor": row.price_minor,
             "currency": row.currency, "location": row.location_label} for row in rows]

@router.get("/{listing_id}")
def get_public_listing(listing_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.get(Listing, listing_id)
    if row is None or row.status != "published":
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"id": row.id, "title": row.title, "description": row.description,
            "price_minor": row.price_minor, "currency": row.currency,
            "location": row.location_label}
