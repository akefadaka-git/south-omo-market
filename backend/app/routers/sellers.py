from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.governance import ensure_marketplace_seller_role
from app.governance_models import BusinessMembership, BusinessMembershipEvent, BusinessProfile
from app.models import Category, Location, SellerProfile, User

router = APIRouter(prefix="/sellers")

BUSINESS_TYPES = {
    "individual", "shop", "producer", "service_provider",
    "cooperative", "company", "trader", "other",
}
CONTACT_METHODS = {"phone", "sms", "email"}
PUBLIC_LOCATION_VISIBILITY = {"hidden", "approximate", "exact"}


class SellerProfileCreate(BaseModel):
    public_name: str = Field(min_length=2, max_length=160)
    location_label: str = Field(min_length=2, max_length=160)
    business_type: str = Field(default="individual", min_length=3, max_length=60)
    legal_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    primary_category_id: str | None = Field(default=None, max_length=36)
    operating_location_id: str | None = Field(default=None, max_length=36)
    service_area: list[str] = Field(default_factory=list, max_length=20)
    operating_hours: dict[str, str] = Field(default_factory=dict)
    supported_languages: list[str] = Field(default_factory=lambda: ["am", "en"], max_length=2)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=254)
    publish_contact_phone: bool = False
    publish_contact_email: bool = False
    public_contact_method: str | None = None
    public_location_visibility: str = "hidden"
    latitude: float | None = None
    longitude: float | None = None
    confirm_exact_location: bool = False
    registration_number: str | None = Field(default=None, max_length=120)


class SellerProfileUpdate(BaseModel):
    public_name: str | None = Field(default=None, min_length=2, max_length=160)
    location_label: str | None = Field(default=None, min_length=2, max_length=160)
    business_type: str | None = Field(default=None, min_length=3, max_length=60)
    legal_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    primary_category_id: str | None = Field(default=None, max_length=36)
    operating_location_id: str | None = Field(default=None, max_length=36)
    service_area: list[str] | None = Field(default=None, max_length=20)
    operating_hours: dict[str, str] | None = None
    supported_languages: list[str] | None = Field(default=None, max_length=2)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=254)
    publish_contact_phone: bool | None = None
    publish_contact_email: bool | None = None
    public_contact_method: str | None = None
    public_location_visibility: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confirm_exact_location: bool = False
    registration_number: str | None = Field(default=None, max_length=120)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _validate_business_fields(
    db: Session,
    *,
    business_type: str,
    category_id: str | None,
    location_id: str | None,
    service_area: list[str],
    supported_languages: list[str],
    public_contact_method: str | None,
    location_visibility: str,
    latitude: float | None,
    longitude: float | None,
    confirm_exact_location: bool,
) -> None:
    if business_type not in BUSINESS_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported business type")
    if category_id is not None:
        category = db.get(Category, category_id)
        if category is None or not category.is_active:
            raise HTTPException(status_code=422, detail="Choose an active business category")
    if location_id is not None:
        location = db.get(Location, location_id)
        if location is None or not location.is_active or location.level not in {"town", "locality"}:
            raise HTTPException(status_code=422, detail="Choose an active town or locality")
    if len(service_area) > 20 or any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in service_area):
        raise HTTPException(status_code=422, detail="Service areas must be up to 20 non-empty locality names")
    if not supported_languages or len(supported_languages) > 2 or not set(supported_languages).issubset({"am", "en"}):
        raise HTTPException(status_code=422, detail="Supported languages must include Amharic and/or English only")
    if public_contact_method is not None and public_contact_method not in CONTACT_METHODS:
        raise HTTPException(status_code=422, detail="Unsupported public contact method")
    if location_visibility not in PUBLIC_LOCATION_VISIBILITY:
        raise HTTPException(status_code=422, detail="Unsupported public location visibility")
    if latitude is not None and not -90 <= latitude <= 90:
        raise HTTPException(status_code=422, detail="Latitude is outside the valid range")
    if longitude is not None and not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="Longitude is outside the valid range")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be supplied together")
    if location_visibility == "exact":
        if latitude is None or longitude is None or not confirm_exact_location:
            raise HTTPException(status_code=422, detail="Exact location requires coordinates and explicit publication consent")
    elif latitude is not None or longitude is not None:
        raise HTTPException(status_code=422, detail="Coordinates are accepted only when exact-location publication is selected")


def _seller_payload(profile: SellerProfile, business: BusinessProfile | None, membership: BusinessMembership | None) -> dict[str, object]:
    result: dict[str, object] = {
        "id": profile.id,
        "public_name": profile.public_name,
        "location": profile.location_label,
        "business_id": profile.business_id,
    }
    if business is None:
        result.update({
            "business_status": None,
            "verification_status": None,
            "membership_status": None,
        })
        return result
    result.update({
        "business_code": business.business_code,
        "display_name": business.display_name,
        "legal_name": business.legal_name,
        "business_type": business.business_type,
        "description": business.description,
        "primary_category_id": business.primary_category_id,
        "operating_location_id": business.operating_location_id,
        "service_area": business.service_area or [],
        "operating_hours": business.operating_hours or {},
        "supported_languages": business.supported_languages or ["am", "en"],
        "contact_phone": business.contact_phone,
        "contact_email": business.contact_email,
        "public_contact_phone": business.public_contact_phone,
        "public_contact_email": business.public_contact_email,
        "public_contact_method": business.public_contact_method,
        "public_location_visibility": business.public_location_visibility,
        "latitude": business.latitude,
        "longitude": business.longitude,
        "registration_number": business.registration_number,
        "business_status": "active" if business.is_active else "inactive",
        "verification_status": business.verification_status,
        "membership_status": membership.status if membership else None,
    })
    return result


def _get_seller_records(db: Session, user_id: str):
    profile = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    business = db.get(BusinessProfile, profile.business_id) if profile.business_id else None
    membership = None
    if business is not None:
        membership = db.scalar(select(BusinessMembership).where(
            BusinessMembership.business_id == business.id,
            BusinessMembership.user_id == user_id,
        ))
    return profile, business, membership


@router.get("/me")
def get_my_seller_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile, business, membership = _get_seller_records(db, user.id)
    return _seller_payload(profile, business, membership)


@router.post("/me", status_code=status.HTTP_201_CREATED)
def create_my_seller_profile(
    payload: SellerProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    existing_profile = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if existing_profile is not None and existing_profile.business_id is not None:
        raise HTTPException(status_code=409, detail="Seller business profile already exists")

    public_name = payload.public_name.strip()
    location_label = payload.location_label.strip()
    if len(public_name) < 2 or len(location_label) < 2:
        raise HTTPException(status_code=422, detail="Public business name and operating locality are required")
    if payload.contact_email and "@" not in payload.contact_email:
        raise HTTPException(status_code=422, detail="Contact email is invalid")
    if payload.publish_contact_phone and not (payload.contact_phone or user.phone_number):
        raise HTTPException(status_code=422, detail="A contact phone is required before publishing it")
    if payload.publish_contact_email and not payload.contact_email:
        raise HTTPException(status_code=422, detail="A contact email is required before publishing it")

    _validate_business_fields(
        db,
        business_type=payload.business_type,
        category_id=payload.primary_category_id,
        location_id=payload.operating_location_id,
        service_area=payload.service_area,
        supported_languages=payload.supported_languages,
        public_contact_method=payload.public_contact_method,
        location_visibility=payload.public_location_visibility,
        latitude=payload.latitude,
        longitude=payload.longitude,
        confirm_exact_location=payload.confirm_exact_location,
    )
    if payload.public_contact_method == "email" and not (payload.publish_contact_email and payload.contact_email):
        raise HTTPException(status_code=422, detail="Publish an email address before selecting email contact")
    if payload.public_contact_method in {"phone", "sms"} and not payload.publish_contact_phone:
        raise HTTPException(status_code=422, detail="Publish a phone number before selecting phone contact")

    business_id = str(uuid4())
    membership_id = str(uuid4())
    now = datetime.now(timezone.utc)
    business = BusinessProfile(
        id=business_id,
        business_code=f"SOM-{uuid4().hex[:12].upper()}",
        legal_name=_clean_text(payload.legal_name) or public_name,
        display_name=public_name,
        business_type=payload.business_type,
        verification_status="pending",
        is_active=True,
        registration_number=_clean_text(payload.registration_number),
        contact_phone=_clean_text(payload.contact_phone) or user.phone_number,
        contact_email=_clean_text(payload.contact_email),
        description=_clean_text(payload.description),
        primary_category_id=payload.primary_category_id,
        operating_location_id=payload.operating_location_id,
        service_area=[item.strip() for item in payload.service_area],
        operating_hours=payload.operating_hours,
        supported_languages=payload.supported_languages,
        public_contact_phone=(_clean_text(payload.contact_phone) or user.phone_number) if payload.publish_contact_phone else None,
        public_contact_email=_clean_text(payload.contact_email) if payload.publish_contact_email else None,
        public_contact_method=payload.public_contact_method,
        public_location_visibility=payload.public_location_visibility,
        latitude=payload.latitude if payload.public_location_visibility == "exact" else None,
        longitude=payload.longitude if payload.public_location_visibility == "exact" else None,
        location_consent_at=now if payload.public_location_visibility == "exact" else None,
    )
    profile = existing_profile or SellerProfile(user_id=user.id)
    profile.business_id = business_id
    profile.public_name = public_name
    profile.location_label = location_label
    membership = BusinessMembership(
        id=membership_id,
        business_id=business_id,
        user_id=user.id,
        membership_role="owner",
        status="pending",
    )
    db.add_all([business, profile, membership])
    db.add(BusinessMembershipEvent(
        id=str(uuid4()),
        business_id=business_id,
        membership_id=membership_id,
        actor_id=user.id,
        event_type="business.profile.submitted",
        event_metadata={"verification_status": "pending"},
    ))
    db.flush()
    ensure_marketplace_seller_role(db, user.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seller or business profile already exists") from None
    db.refresh(profile)
    db.refresh(business)
    db.refresh(membership)
    return _seller_payload(profile, business, membership)


@router.patch("/me")
def update_my_seller_profile(
    payload: SellerProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile, business, membership = _get_seller_records(db, user.id)
    if business is None:
        raise HTTPException(status_code=409, detail="This seller profile needs business onboarding before it can be edited")
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(key, object()) is None for key in ("public_name", "location_label", "business_type", "public_location_visibility") if key in changes):
        raise HTTPException(status_code=422, detail="Required seller profile fields cannot be null")
    if "contact_email" in changes and changes["contact_email"] and "@" not in changes["contact_email"]:
        raise HTTPException(status_code=422, detail="Contact email is invalid")

    public_name = changes.get("public_name", profile.public_name)
    location_label = changes.get("location_label", profile.location_label)
    business_type = changes.get("business_type", business.business_type)
    category_id = changes.get("primary_category_id", business.primary_category_id)
    location_id = changes.get("operating_location_id", business.operating_location_id)
    service_area = changes.get("service_area", business.service_area or [])
    supported_languages = changes.get("supported_languages", business.supported_languages or ["am", "en"])
    contact_method = changes.get("public_contact_method", business.public_contact_method)
    visibility = changes.get("public_location_visibility", business.public_location_visibility)
    latitude = changes.get("latitude", business.latitude)
    longitude = changes.get("longitude", business.longitude)
    confirm_exact = changes.get("confirm_exact_location", False)
    if visibility != "exact" and ("public_location_visibility" in changes or "latitude" in changes or "longitude" in changes):
        latitude = longitude = None
    _validate_business_fields(
        db,
        business_type=business_type,
        category_id=category_id,
        location_id=location_id,
        service_area=service_area,
        supported_languages=supported_languages,
        public_contact_method=contact_method,
        location_visibility=visibility,
        latitude=latitude,
        longitude=longitude,
        confirm_exact_location=confirm_exact or (
            visibility == "exact" and "public_location_visibility" not in changes
            and "latitude" not in changes and "longitude" not in changes
        ),
    )

    if "public_name" in changes:
        profile.public_name = public_name.strip()
        business.display_name = public_name.strip()
    if "location_label" in changes:
        profile.location_label = location_label.strip()
    for key in ("business_type", "legal_name", "description", "primary_category_id",
                "operating_location_id", "service_area", "operating_hours",
                "supported_languages", "registration_number"):
        if key in changes:
            value = changes[key]
            if key in {"legal_name", "description", "registration_number"}:
                value = _clean_text(value)
            if key == "service_area":
                value = [item.strip() for item in value]
            setattr(business, key, value)
    if "contact_phone" in changes:
        business.contact_phone = _clean_text(changes["contact_phone"])
    if "contact_email" in changes:
        business.contact_email = _clean_text(changes["contact_email"])
    if changes.get("publish_contact_phone") is True:
        business.public_contact_phone = business.contact_phone or user.phone_number
    elif changes.get("publish_contact_phone") is False:
        business.public_contact_phone = None
    if changes.get("publish_contact_email") is True:
        if not business.contact_email:
            raise HTTPException(status_code=422, detail="A contact email is required before publishing it")
        business.public_contact_email = business.contact_email
    elif changes.get("publish_contact_email") is False:
        business.public_contact_email = None
    if "public_contact_method" in changes:
        if contact_method == "email" and not business.public_contact_email:
            raise HTTPException(status_code=422, detail="Publish an email address before selecting email contact")
        if contact_method in {"phone", "sms"} and not business.public_contact_phone:
            raise HTTPException(status_code=422, detail="Publish a phone number before selecting phone contact")
        business.public_contact_method = contact_method
    if "public_location_visibility" in changes or "latitude" in changes or "longitude" in changes:
        business.public_location_visibility = visibility
        business.latitude = latitude if visibility == "exact" else None
        business.longitude = longitude if visibility == "exact" else None
        business.location_consent_at = datetime.now(timezone.utc) if visibility == "exact" else None
    db.commit()
    db.refresh(profile)
    db.refresh(business)
    return _seller_payload(profile, business, membership)
