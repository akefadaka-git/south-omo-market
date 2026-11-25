import re
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, inspect as sqlalchemy_inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.image_storage import ListingImageStorage, get_image_storage
from app.dependencies import get_current_user
from app.governance import require_marketplace_listing_policy, require_seller_business_listing_access
from app.models import AuditEvent, Category, Listing, ListingEdit, ListingImage, Location, SellerProfile, User
from app.governance_models import BusinessMembership, BusinessProfile

router = APIRouter(prefix="/listings")


class ListingCreate(BaseModel):
    category_id: str
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=5000)
    attributes: dict[str, object] = Field(default_factory=dict)
    price_minor: int = Field(ge=0)
    location_label: str = Field(min_length=2, max_length=160)
    location_id: str | None = None


class ListingUpdate(BaseModel):
    category_id: str | None = None
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    attributes: dict[str, object] | None = None
    price_minor: int | None = Field(default=None, ge=0)
    location_label: str | None = Field(default=None, min_length=2, max_length=160)
    location_id: str | None = None


class ListingSyncCreate(ListingCreate):
    client_sync_id: UUID



def _validated_attributes(category: Category, values: dict[str, object]) -> dict[str, object]:
    """Validate submitted values against the active leaf category's schema."""
    import math

    schema = category.attributes_schema or []
    if not isinstance(schema, list):
        raise HTTPException(status_code=500, detail="Category attribute schema is invalid")

    definitions: dict[str, dict[str, object]] = {}
    supported_types = {"text", "number", "boolean", "choice"}
    for item in schema:
        if not isinstance(item, dict):
            raise HTTPException(status_code=500, detail="Category attribute schema is invalid")
        key = item.get("key")
        kind = item.get("type")
        if not isinstance(key, str) or not key.strip() or key != key.strip() or key in definitions:
            raise HTTPException(status_code=500, detail="Category attribute schema has an invalid or duplicate key")
        if not isinstance(kind, str) or kind not in supported_types or not isinstance(item.get("required", False), bool):
            raise HTTPException(status_code=500, detail=f"Category attribute schema is invalid for {key}")
        if kind == "text":
            maximum = item.get("max_length", 500)
            if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
                raise HTTPException(status_code=500, detail=f"Category text limit is invalid for {key}")
        if kind == "number":
            minimum = item.get("min")
            maximum = item.get("max")
            for bound in (minimum, maximum):
                if bound is not None and (
                    isinstance(bound, bool) or not isinstance(bound, (int, float))
                    or (isinstance(bound, float) and not math.isfinite(bound))
                ):
                    raise HTTPException(status_code=500, detail=f"Category numeric bound is invalid for {key}")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise HTTPException(status_code=500, detail=f"Category numeric range is invalid for {key}")
        if kind == "choice":
            options = item.get("options")
            if (
                not isinstance(options, list) or not options
                or any(not isinstance(option, str) or not option.strip() for option in options)
                or len(options) != len(set(options))
            ):
                raise HTTPException(status_code=500, detail=f"Category options are invalid for {key}")
        definitions[key] = item

    unknown = set(values) - set(definitions)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"attributes": f"Unknown fields: {', '.join(sorted(unknown))}"},
        )

    cleaned: dict[str, object] = {}
    for key, definition in definitions.items():
        value = values.get(key)
        kind = definition["type"]
        if value is None:
            if definition.get("required", False):
                raise HTTPException(status_code=422, detail={"attributes": f"{key} is required"})
            continue

        if kind == "text":
            if not isinstance(value, str):
                raise HTTPException(status_code=422, detail={"attributes": f"Invalid value for {key}"})
            value = value.strip()
            if not value and definition.get("required", False):
                raise HTTPException(status_code=422, detail={"attributes": f"{key} is required"})
            if len(value) > int(definition.get("max_length", 500)):
                raise HTTPException(status_code=422, detail={"attributes": f"Text is too long for {key}"})
        elif kind == "number":
            if (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or (isinstance(value, float) and not math.isfinite(value))
            ):
                raise HTTPException(status_code=422, detail={"attributes": f"Invalid number for {key}"})
            if (
                ("min" in definition and value < definition["min"])
                or ("max" in definition and value > definition["max"])
            ):
                raise HTTPException(status_code=422, detail={"attributes": f"Value out of range for {key}"})
        elif kind == "boolean":
            if not isinstance(value, bool):
                raise HTTPException(status_code=422, detail={"attributes": f"Invalid boolean for {key}"})
        elif kind == "choice":
            if not isinstance(value, str) or value not in definition["options"]:
                raise HTTPException(status_code=422, detail={"attributes": f"Invalid choice for {key}"})
        cleaned[key] = value
    return cleaned


def _is_minor_text_normalization(current: str, proposed: str) -> bool:
    """Permit punctuation/case/spacing cleanup only; token changes need review."""
    def word_tokens(value: str) -> list[str]:
        return re.findall(r"\w+", value.casefold(), flags=re.UNICODE)

    return current != proposed and word_tokens(current) == word_tokens(proposed)


def _require_leaf_category(db: Session, category: Category) -> None:
    # Persisted governance roots protect the category and all descendants even
    # if a display slug is later renamed. The slug check is a fail-safe for
    # pre-migration or incomplete reference-data states.
    protected_roots: set[str] = set()
    # Some isolated legacy tests and pre-upgrade contexts use a reduced schema.
    # Consult the persisted policy table when present; otherwise retain the
    # immutable legacy slug guard and ancestry traversal.
    if hasattr(db, "get_bind"):
        bind = db.get_bind()
        if sqlalchemy_inspect(bind).has_table("protected_category_roots"):
            protected_roots = set(db.execute(text("""
                SELECT category_id FROM protected_category_roots
                WHERE seller_listing_allowed=FALSE AND applies_to_descendants=TRUE
            """)).scalars().all())
    ancestor: Category | None = category
    seen: set[str] = set()
    protected = False
    while ancestor is not None and ancestor.id not in seen:
        seen.add(ancestor.id)
        if ancestor.id in protected_roots or ancestor.slug == "work-opportunities":
            protected = True
            break
        ancestor = db.get(Category, ancestor.parent_id) if ancestor.parent_id else None
    if protected:
        raise HTTPException(
            status_code=403,
            detail="Employment opportunities must use the Owner-controlled employment agency",
        )

    if db.scalar(select(Category.id).where(
        Category.parent_id == category.id, Category.is_active.is_(True)
    )) is not None:
        raise HTTPException(status_code=422, detail="Choose a subcategory before creating a listing")

def _resolve_location_id(db: Session, location_id: str | None, location_label: str) -> str | None:
    if location_id is not None:
        location = db.get(Location, location_id)
        if location is None or not location.is_active:
            raise HTTPException(status_code=404, detail="Location not found")
        return location.id
    return db.scalar(
        select(Location.id).where(
            func.lower(Location.name_en) == location_label.strip().lower(),
            Location.is_active.is_(True),
        )
    )


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
        "seller_id": row.seller_id,
        "category_id": row.category_id,
        "title": row.title,
        "description": row.description,
        "attributes": row.attributes or {},
        "price_minor": row.price_minor,
        "currency": row.currency,
        "location": row.location_label,
        "location_id": row.location_id,
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
    location_id: str | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=120),
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = (
        select(Listing)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .join(User, SellerProfile.user_id == User.id)
        .join(BusinessProfile, BusinessProfile.id == SellerProfile.business_id)
        .where(
            BusinessProfile.is_active.is_(True),
            BusinessProfile.verification_status == "verified",
            exists(select(BusinessMembership.id).where(
                BusinessMembership.business_id == BusinessProfile.id,
                BusinessMembership.status == "active",
                BusinessMembership.membership_role.in_(("owner", "administrator", "manager", "staff")),
                (BusinessMembership.expires_at.is_(None) | (BusinessMembership.expires_at > func.now())),
            )),
            Listing.status == "published",
            User.is_active.is_(True),
            User.is_suspended.is_(False),
        )
    )
    if category_id:
        query = query.where(Listing.category_id == category_id)
    if location_id:
        query = query.where(Listing.location_id == location_id)
    if q:
        term = f"%{q.strip().casefold()}%"
        query = query.where(
            func.lower(Listing.title).like(term)
            | func.lower(Listing.description).like(term)
            | func.lower(Listing.location_label).like(term)
        )
    ordering = {
        "newest": (Listing.created_at.desc(), Listing.id),
        "price_asc": (Listing.price_minor.asc(), Listing.created_at.desc(), Listing.id),
        "price_desc": (Listing.price_minor.desc(), Listing.created_at.desc(), Listing.id),
    }[sort]
    rows = db.scalars(
        query.order_by(*ordering).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "category_id": row.category_id,
            "price_minor": row.price_minor,
            "currency": row.currency,
            "location": row.location_label,
            "location_id": row.location_id,
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
    category = db.get(Category, payload.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    _require_leaf_category(db, category)
    require_seller_business_listing_access(db, user)
    require_marketplace_listing_policy(
        db, user, action="marketplace.listing.sync", category_id=category.id
    )
    resolved_location_id = _resolve_location_id(db, payload.location_id, payload.location_label)
    sync_id = str(payload.client_sync_id)
    existing = db.scalar(select(Listing).where(Listing.client_sync_id == sync_id))
    if existing is not None:
        if existing.seller_id != seller.id:
            raise HTTPException(status_code=409, detail="Sync identifier is already in use")
        expected = payload.model_dump(exclude={"client_sync_id"})
        expected["location_id"] = resolved_location_id
        actual = {
            "category_id": existing.category_id,
            "title": existing.title,
            "description": existing.description,
            "attributes": existing.attributes or {},
            "price_minor": existing.price_minor,
            "location_label": existing.location_label,
            "location_id": existing.location_id,
        }
        if expected != actual:
            raise HTTPException(status_code=409, detail="Sync identifier was reused with different draft data")
        return {"id": existing.id, "status": existing.status, "idempotent": True}

    attributes = _validated_attributes(category, payload.attributes)
    listing = Listing(
        seller_id=seller.id,
        category_id=category.id,
        title=payload.title,
        description=payload.description,
        attributes=attributes,
        price_minor=payload.price_minor,
        location_label=payload.location_label,
        location_id=resolved_location_id,
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
        expected["location_id"] = resolved_location_id
        actual = {
            "category_id": existing.category_id,
            "title": existing.title,
            "description": existing.description,
            "attributes": existing.attributes or {},
            "price_minor": existing.price_minor,
            "location_label": existing.location_label,
            "location_id": existing.location_id,
        }
        if expected != actual:
            raise HTTPException(status_code=409, detail="Sync identifier was reused with different draft data")
        return {"id": existing.id, "status": existing.status, "idempotent": True}
    db.refresh(listing)
    return {"id": listing.id, "status": listing.status, "idempotent": False}


@router.get("/{listing_id}")
def get_public_listing(listing_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.scalar(
        select(Listing)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .join(User, SellerProfile.user_id == User.id)
        .join(BusinessProfile, BusinessProfile.id == SellerProfile.business_id)
        .where(
            BusinessProfile.is_active.is_(True),
            BusinessProfile.verification_status == "verified",
            exists(select(BusinessMembership.id).where(
                BusinessMembership.business_id == BusinessProfile.id,
                BusinessMembership.status == "active",
                BusinessMembership.membership_role.in_(("owner", "administrator", "manager", "staff")),
                (BusinessMembership.expires_at.is_(None) | (BusinessMembership.expires_at > func.now())),
            )),
            Listing.id == listing_id,
            Listing.status == "published",
            User.is_active.is_(True),
            User.is_suspended.is_(False),
        )
    )
    if row is None:
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
    _require_leaf_category(db, category)
    require_seller_business_listing_access(db, user)
    require_marketplace_listing_policy(
        db, user, action="marketplace.listing.create", category_id=category.id
    )
    attributes = _validated_attributes(category, payload.attributes)
    resolved_location_id = _resolve_location_id(db, payload.location_id, payload.location_label)
    listing = Listing(
        seller_id=seller.id, category_id=category.id,
        title=payload.title, description=payload.description, attributes=attributes,
        price_minor=payload.price_minor, location_label=payload.location_label,
        location_id=resolved_location_id, status="draft",
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
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing = db.scalar(
        select(Listing).where(
            Listing.id == listing_id, Listing.seller_id == seller.id
        ).with_for_update()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status not in {"draft", "published"}:
        raise HTTPException(status_code=409, detail="Only draft or published listings can be edited")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _listing_summary(listing)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Listing fields cannot be null")
    require_seller_business_listing_access(db, user)
    category = db.get(Category, changes.get("category_id", listing.category_id))
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    _require_leaf_category(db, category)
    require_marketplace_listing_policy(
        db, user, action="marketplace.listing.update", category_id=category.id
    )
    if "location_id" in changes or "location_label" in changes:
        if "location_id" in changes:
            location_id = changes["location_id"]
        elif "location_label" in changes:
            location_id = _resolve_location_id(db, None, changes["location_label"])
        else:
            location_id = listing.location_id
        if location_id is not None:
            location = db.get(Location, location_id)
            if location is None or not location.is_active:
                raise HTTPException(status_code=404, detail="Location not found")
        changes["location_id"] = location_id
    if "category_id" in changes or "attributes" in changes:
        candidate_attributes = changes.get("attributes", listing.attributes or {})
        changes["attributes"] = _validated_attributes(category, candidate_attributes)

    if listing.status == "draft":
        for field, value in changes.items():
            setattr(listing, field, value)
        db.commit()
        db.refresh(listing)
        return _listing_summary(listing)

    # A single pending edit per listing prevents stale proposals and concurrent
    # minor edits from changing the approved baseline while review is underway.
    pending = db.scalar(select(ListingEdit.id).where(
        ListingEdit.listing_id == listing.id,
        ListingEdit.status == "pending_review",
    ))
    if pending is not None:
        raise HTTPException(status_code=409, detail="A listing edit is already awaiting moderation")

    # Published content is immutable while a material edit is reviewed.
    # Only description formatting changes preserving all Unicode word tokens
    # are eligible for direct publication; wording/claims require moderation.
    if set(changes) == {"description"} and _is_minor_text_normalization(
        listing.description, str(changes["description"])
    ):
        previous_description = listing.description
        listing.description = str(changes["description"])
        db.add(AuditEvent(
            actor_id=user.id,
            action="listing.minor_correction.published",
            resource_type="listing",
            resource_id=listing.id,
            event_metadata={
                "changed_fields": ["description"],
                "previous_description": previous_description,
                "new_description": listing.description,
            },
        ))
        db.commit()
        db.refresh(listing)
        return {**_listing_summary(listing), "edit_status": "published_minor_correction"}

    edit = ListingEdit(
        listing_id=listing.id,
        submitted_by=user.id,
        proposed_values=changes,
        changed_fields=sorted(changes),
        status="pending_review",
        pending_key="pending",
    )
    db.add(edit)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A listing edit is already awaiting moderation") from None
    db.refresh(edit)
    return {
        "id": listing.id,
        "status": listing.status,
        "edit_id": edit.id,
        "edit_status": edit.status,
        "changed_fields": edit.changed_fields,
    }


@router.post("/{listing_id}/images", status_code=status.HTTP_201_CREATED)
async def upload_listing_image(
    listing_id: str,
    client_image_id: UUID = Form(...),
    file: UploadFile = File(...),
    storage: ListingImageStorage = Depends(get_image_storage),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    seller = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if seller is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing = db.scalar(
        select(Listing).where(
            Listing.id == listing_id, Listing.seller_id == seller.id
        ).with_for_update()
    )
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    require_seller_business_listing_access(db, user)
    if listing.status != "draft":
        raise HTTPException(status_code=409, detail="Images can only be added to draft listings")
    image_key = str(client_image_id)
    existing = db.scalar(select(ListingImage).where(ListingImage.client_image_id == image_key))
    if existing is not None:
        if existing.listing_id != listing.id:
            raise HTTPException(status_code=409, detail="Image identifier is already in use")
        return _image_payload(existing)

    settings = get_settings()
    image_count = db.scalar(
        select(func.count(ListingImage.id)).where(ListingImage.listing_id == listing.id)
    ) or 0
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
            if len(clean_bytes) > settings.max_listing_image_bytes:
                raise HTTPException(status_code=413, detail="Normalized image exceeds the upload size limit")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid supported image") from None

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
    storage: ListingImageStorage = Depends(get_image_storage),
    db: Session = Depends(get_db),
) -> Response:
    row = db.scalar(
        select(ListingImage)
        .join(Listing, ListingImage.listing_id == Listing.id)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .join(User, SellerProfile.user_id == User.id)
        .join(BusinessProfile, BusinessProfile.id == SellerProfile.business_id)
        .where(
            BusinessProfile.is_active.is_(True),
            BusinessProfile.verification_status == "verified",
            exists(select(BusinessMembership.id).where(
                BusinessMembership.business_id == BusinessProfile.id,
                BusinessMembership.status == "active",
                BusinessMembership.membership_role.in_(("owner", "administrator", "manager", "staff")),
                (BusinessMembership.expires_at.is_(None) | (BusinessMembership.expires_at > func.now())),
            )),
            ListingImage.id == image_id,
            Listing.id == listing_id,
            Listing.status == "published",
            User.is_active.is_(True),
            User.is_suspended.is_(False),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        content = storage.read(row.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found") from None
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/{listing_id}/submit", status_code=status.HTTP_200_OK)
def submit_my_listing(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = _owned_listing(db, user, listing_id)
    if listing.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft listings can be submitted")
    # Revalidate legacy drafts at the submission boundary; older records may
    # predate the seller-side restriction on Owner-managed employment categories.
    category = db.get(Category, listing.category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Category not found")
    _require_leaf_category(db, category)
    require_seller_business_listing_access(db, user)
    require_marketplace_listing_policy(
        db, user, action="marketplace.listing.submit", category_id=category.id
    )
    listing.status = "pending_review"
    db.commit()
    return {"id": listing.id, "status": listing.status}
