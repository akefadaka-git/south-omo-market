from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Inquiry, Listing, User

router = APIRouter(prefix="/inquiries")

class InquiryCreate(BaseModel):
    listing_id: str
    message: str = Field(min_length=1, max_length=2000)

@router.post("", status_code=status.HTTP_201_CREATED)
def create_inquiry(
    payload: InquiryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.get(Listing, payload.listing_id)
    if listing is None or listing.status != "published":
        raise HTTPException(status_code=404, detail="Listing not found")
    inquiry = Inquiry(
        listing_id=listing.id,
        buyer_name=user.display_name,
        contact_value=user.phone_number,
        message=payload.message,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return {"id": inquiry.id, "status": "received"}
