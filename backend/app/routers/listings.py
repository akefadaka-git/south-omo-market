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


class ListingUpdate(BaseModel):
    category_id: str | None = None
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    price_minor: int | None = Field(default=None, ge=0)
    location_label: str | None = Field(default=None, min_length=2, max_length=160)


def _listing_summary(row: Listing) -> dict[str, object]:
    return {
        "id": row.id,
        "category_id": row.category_id,
        "title": row.title,
        "description": row.description,
        "price_minor": row.price_minor,
        "currency": row.currency,
        "location": row.location_label,
        "status": row.status,
    }


def _owned_listing(db: Session, user: User, listing_id: str) -> Listing:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing = db.scalar(
        select(Listing).where(Listing.id == listing_id, Listing.seller_id == seller.id)
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("")
def list_public_listings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = select(Listing).where(Listing.status == "published")
    if category_id:
        query = query.where(Listing.category_id == category_id)
    rows = db.scalars(
        query.order_by(Listing.created_at.desc(), Listing.id).offset(offset).limit(limit)
    ).all()
    return [
        {"id": row.id, "title": row.title, "price_minor": row.price_minor,
         "currency": row.currency, "location": row.location_label}
        for row in rows
    ]


@router.get("/my")
def list_my_listings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        return []
    rows = db.scalars(
        select(Listing).where(Listing.seller_id == seller.id)
        .order_by(Listing.created_at.desc(), Listing.id)
    ).all()
    return [_listing_summary(row) for row in rows]


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
    category = db.get(Category, payload.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    listing = Listing(
        seller_id=seller.id, category_id=category.id,
        title=payload.title, description=payload.description,
        price_minor=payload.price_minor, location_label=payload.location_label,
        status="draft",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "status": "draft"}


@router.patch("/{listing_id}")
def update_my_listing(
    listing_id: str,
    payload: ListingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    listing = _owned_listing(db, user, listing_id)
    if listing.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft listings can be edited")
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Listing fields cannot be null")
    if "category_id" in changes:
        category = db.get(Category, changes["category_id"])
        if category is None or not category.is_active:
            raise HTTPException(status_code=404, detail="Category not found")
    for field, value in changes.items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return _listing_summary(listing)


@router.post("/{listing_id}/submit", status_code=status.HTTP_200_OK)
def submit_my_listing(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = _owned_listing(db, user, listing_id)
    if listing.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft listings can be submitted")
    listing.status = "pending_review"
    db.commit()
    return {"id": listing.id, "status": listing.status}
