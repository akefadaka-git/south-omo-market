from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import SellerProfile, User
from app.governance import ensure_marketplace_seller_role
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sellers")

class SellerProfileCreate(BaseModel):
    public_name: str = Field(min_length=2, max_length=160)
    location_label: str = Field(min_length=2, max_length=160)

@router.get("/me")
def get_my_seller_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    profile = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    return {"id": profile.id, "public_name": profile.public_name, "location": profile.location_label}


@router.post("/me", status_code=status.HTTP_201_CREATED)
def create_my_seller_profile(
    payload: SellerProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    existing = db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Seller profile already exists")
    profile = SellerProfile(user_id=user.id, **payload.model_dump())
    db.add(profile)
    db.flush()
    ensure_marketplace_seller_role(db, user.id)
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "public_name": profile.public_name, "location": profile.location_label}
