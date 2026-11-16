from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Category, Listing, SellerProfile, User

router = APIRouter(prefix="/listings")

class ListingCreate(BaseModel):
    category_id: str
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=5000)
    price_minor: int = Field(ge=0)
    location_label: str = Field(min_length=2, max_length=160)

@router.get("")
def list_public_listings(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.scalars(
        select(Listing).where(Listing.status == "published")
        .order_by(Listing.created_at.desc()).limit(limit)
    ).all()
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

@router.post("", status_code=status.HTTP_201_CREATED)
def create_my_listing(
    payload: ListingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=409, detail="Create a seller profile before listing")
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    listing = Listing(
        seller_id=seller.id, category_id=payload.category_id,
        title=payload.title, description=payload.description,
        price_minor=payload.price_minor, location_label=payload.location_label,
        status="draft",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "status": "draft"}
