from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
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
        "profile_photo_key": profile.profile_photo_key,
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
