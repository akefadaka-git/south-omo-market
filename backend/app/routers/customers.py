from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.image_storage import ListingImageStorage, get_image_storage
from app.dependencies import get_current_user
from app.models import CustomerProfile, User
from app.routers.identity import validate_preferred_references
from app.schemas import CustomerProfileUpdate

router = APIRouter(prefix="/customers")


def _profile_payload(user: User, profile: CustomerProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "user_id": user.id,
        "phone_number": user.phone_number,
        "display_name": user.display_name,
        "preferred_location_id": profile.preferred_location_id,
        "preferred_market_id": profile.preferred_market_id,
        "preferred_language": profile.preferred_language,
        "email": profile.email,
        "profile_photo_url": "/customers/me/photo" if profile.profile_photo_key else None,
        "contact_preference": profile.contact_preference,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("/me")
def get_my_customer_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = db.query(CustomerProfile).filter_by(user_id=user.id).one_or_none()
    if profile is None:
        # Backward compatibility for accounts created before customer profiles.
        profile = CustomerProfile(user_id=user.id, preferred_language="am")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return _profile_payload(user, profile)


@router.patch("/me")
def update_my_customer_profile(
    payload: CustomerProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = db.query(CustomerProfile).filter_by(user_id=user.id).one_or_none()
    if profile is None:
        profile = CustomerProfile(user_id=user.id, preferred_language="am")
        db.add(profile)
        db.flush()

    changes = payload.model_dump(exclude_unset=True)
    if "display_name" in changes and changes["display_name"] is None:
        raise HTTPException(status_code=422, detail="Display name cannot be null")
    if "preferred_language" in changes and changes["preferred_language"] is None:
        raise HTTPException(status_code=422, detail="Preferred language cannot be null")
    location_id = changes.get("preferred_location_id", profile.preferred_location_id)
    market_id = changes.get("preferred_market_id", profile.preferred_market_id)
    validate_preferred_references(db, location_id, market_id)

    if "display_name" in changes:
        user.display_name = changes.pop("display_name")
    for key, value in changes.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    db.refresh(user)
    return _profile_payload(user, profile)


@router.post("/me/photo", status_code=201)
async def upload_my_customer_photo(
    file: UploadFile = File(...),
    storage: ListingImageStorage = Depends(get_image_storage),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    raw = await file.read(settings.max_listing_image_bytes + 1)
    await file.close()
    if not raw or len(raw) > settings.max_listing_image_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the upload size limit")
    try:
        with Image.open(BytesIO(raw)) as probe:
            if probe.format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are accepted")
            width, height = probe.size
            if width < 1 or height < 1 or width * height > settings.max_listing_image_pixels:
                raise HTTPException(status_code=413, detail="Image dimensions exceed the allowed limit")
            probe.verify()
        with Image.open(BytesIO(raw)) as source:
            normalized = ImageOps.exif_transpose(source).convert("RGB")
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=88, optimize=True)
            clean_bytes = output.getvalue()
            if len(clean_bytes) > settings.max_listing_image_bytes:
                raise HTTPException(status_code=413, detail="Normalized image exceeds the upload size limit")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid supported image") from None

    profile = db.query(CustomerProfile).filter_by(user_id=user.id).one_or_none()
    if profile is None:
        profile = CustomerProfile(user_id=user.id, preferred_language="am")
        db.add(profile)
        db.flush()
    new_key = storage.save_customer_jpeg(user.id, clean_bytes)
    previous_key = profile.profile_photo_key
    profile.profile_photo_key = new_key
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_customer_jpeg(new_key, user.id)
        raise
    if previous_key:
        storage.delete_customer_jpeg(previous_key, user.id)
    return {"profile_photo_url": "/customers/me/photo"}


@router.get("/me/photo")
def get_my_customer_photo(
    storage: ListingImageStorage = Depends(get_image_storage),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    profile = db.query(CustomerProfile).filter_by(user_id=user.id).one_or_none()
    if profile is None or not profile.profile_photo_key:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    try:
        content = storage.read_customer_jpeg(profile.profile_photo_key, user.id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Profile photo not found") from None
    return Response(content=content, media_type="image/jpeg",
                    headers={"Cache-Control": "private, no-store"})


@router.delete("/me/photo", status_code=204)
def delete_my_customer_photo(
    storage: ListingImageStorage = Depends(get_image_storage),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    profile = db.query(CustomerProfile).filter_by(user_id=user.id).one_or_none()
    if profile is None or not profile.profile_photo_key:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    previous_key = profile.profile_photo_key
    profile.profile_photo_key = None
    db.commit()
    storage.delete_customer_jpeg(previous_key, user.id)
    return Response(status_code=204)
