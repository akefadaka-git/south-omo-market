from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.image_storage import LocalImageStorage
from app.dependencies import get_current_user
from app.models import Category, Listing, ListingImage, SellerProfile, User

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


class ListingSyncCreate(ListingCreate):
    client_sync_id: UUID


def _image_payload(image: ListingImage) -> dict[str, object]:
    return {
        "id": image.id,
        "url": f"/api/v1/listings/{image.listing_id}/images/{image.id}",
        "width": image.width,
        "height": image.height,
        "size_bytes": image.size_bytes,
    }


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
        "images": [_image_payload(image) for image in row.images],
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
        {
            "id": row.id,
            "title": row.title,
            "price_minor": row.price_minor,
            "currency": row.currency,
            "location": row.location_label,
            "images": [_image_payload(image) for image in row.images],
        }
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


@router.post("/sync", status_code=status.HTTP_200_OK)
def sync_my_offline_draft(
    payload: ListingSyncCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=409, detail="Create a seller profile before syncing drafts")
    sync_id = str(payload.client_sync_id)
    existing = db.scalar(select(Listing).where(Listing.client_sync_id == sync_id))
    if existing is not None:
        if existing.seller_id != seller.id:
            raise HTTPException(status_code=409, detail="Sync identifier is already in use")
        expected = payload.model_dump(exclude={"client_sync_id"})
        actual = {
            "category_id": existing.category_id,
            "title": existing.title,
            "description": existing.description,
            "price_minor": existing.price_minor,
            "location_label": existing.location_label,
        }
        if expected != actual:
            raise HTTPException(status_code=409, detail="Sync identifier was reused with different draft data")
        return {"id": existing.id, "status": existing.status, "idempotent": True}

    category = db.get(Category, payload.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    listing = Listing(
        seller_id=seller.id,
        category_id=category.id,
        title=payload.title,
        description=payload.description,
        price_minor=payload.price_minor,
        location_label=payload.location_label,
        status="draft",
        client_sync_id=sync_id,
    )
    db.add(listing)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Listing).where(Listing.client_sync_id == sync_id))
        if existing is None or existing.seller_id != seller.id:
            raise HTTPException(status_code=409, detail="Sync identifier is already in use")
        expected = payload.model_dump(exclude={"client_sync_id"})
        actual = {
            "category_id": existing.category_id,
            "title": existing.title,
            "description": existing.description,
            "price_minor": existing.price_minor,
            "location_label": existing.location_label,
        }
        if expected != actual:
            raise HTTPException(status_code=409, detail="Sync identifier was reused with different draft data")
        return {"id": existing.id, "status": existing.status, "idempotent": True}
    db.refresh(listing)
    return {"id": listing.id, "status": listing.status, "idempotent": False}


@router.get("/{listing_id}")
def get_public_listing(listing_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.get(Listing, listing_id)
    if row is None or row.status != "published":
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_summary(row)


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


@router.post("/{listing_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_listing_image(
    listing_id: str,
    client_image_id: UUID = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    listing = _owned_listing(db, user, listing_id)
    if listing.status != "draft":
        raise HTTPException(status_code=409, detail="Images can only be added to draft listings")
    image_key = str(client_image_id)
    existing = db.scalar(select(ListingImage).where(ListingImage.client_image_id == image_key))
    if existing is not None:
        if existing.listing_id != listing.id:
            raise HTTPException(status_code=409, detail="Image identifier is already in use")
        return _image_payload(existing)

    settings = get_settings()
    current_count = db.scalar(
        select(ListingImage.id).where(ListingImage.listing_id == listing.id)
    )
    image_count = len(listing.images)
    if image_count >= settings.max_listing_images:
        raise HTTPException(status_code=409, detail="Listing image limit reached")

    raw = await file.read(settings.max_listing_image_bytes + 1)
    await file.close()
    if not raw or len(raw) > settings.max_listing_image_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB upload limit")

    try:
        with Image.open(BytesIO(raw)) as probe:
            if probe.format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are accepted")
            width, height = probe.size
            if width < 1 or height < 1 or width * height > settings.max_listing_image_pixels:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the allowed limit")
            probe.verify()
        with Image.open(BytesIO(raw)) as source:
            oriented = ImageOps.exif_transpose(source)
            normalized = oriented.convert("RGB")
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=88, optimize=True)
            clean_bytes = output.getvalue()
            width, height = normalized.size
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid supported image") from None

    storage = LocalImageStorage()
    key = storage.save_jpeg(listing.id, clean_bytes)
    record = ListingImage(
        listing_id=listing.id,
        client_image_id=image_key,
        storage_key=key,
        content_type="image/jpeg",
        size_bytes=len(clean_bytes),
        width=width,
        height=height,
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    db.refresh(record)
    return _image_payload(record)


@router.get("/{listing_id}/images/{image_id}")
def get_public_listing_image(
    listing_id: str,
    image_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    row = db.scalar(
        select(ListingImage)
        .join(Listing, ListingImage.listing_id == Listing.id)
        .where(
            ListingImage.id == image_id,
            Listing.id == listing_id,
            Listing.status == "published",
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        path = LocalImageStorage().resolve(row.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    return FileResponse(path, media_type="image/jpeg", filename=f"{row.id}.jpg")


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
