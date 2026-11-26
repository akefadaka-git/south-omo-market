from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.dependencies import get_current_user
from app.models import AuditEvent, Listing, Report, SellerProfile, User

router = APIRouter(prefix="/reports", tags=["reports"])

ReportReason = Literal[
    "fraud", "misleading_information", "prohibited_item", "harassment",
    "unsafe_activity", "impersonation", "spam", "other",
]


class EvidencePayload(BaseModel):
    summary: str = Field(min_length=1, max_length=3000)
    reference: str | None = Field(default=None, max_length=500)


class ReportCreate(BaseModel):
    listing_id: str | None = None
    seller_id: str | None = None
    reason: ReportReason
    description: str = Field(min_length=10, max_length=4000)
    evidence: list[EvidencePayload] = Field(default_factory=list, max_length=5)


def _target_or_404(db: Session, listing_id: str | None, seller_id: str | None):
    if (listing_id is None) == (seller_id is None):
        raise HTTPException(status_code=422, detail="Provide exactly one listing_id or seller_id")
    if listing_id is not None:
        listing = db.get(Listing, listing_id)
        if listing is None:
            raise HTTPException(status_code=404, detail="Listing not found")
        return listing, None
    seller = db.get(SellerProfile, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    return None, seller


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def create_report(
    request: Request,
    response: Response,
    payload: ReportCreate,
    reporter: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    listing, seller = _target_or_404(db, payload.listing_id, payload.seller_id)
    if seller is not None and seller.user_id == reporter.id:
        raise HTTPException(status_code=422, detail="You cannot report your own seller account")
    if listing is not None:
        owner = db.get(SellerProfile, listing.seller_id)
        if owner is not None and owner.user_id == reporter.id:
            raise HTTPException(status_code=422, detail="You cannot report your own listing")
    report = Report(
        id=str(uuid4()),
        reporter_user_id=reporter.id,
        listing_id=listing.id if listing else None,
        seller_id=seller.id if seller else None,
        reason=payload.reason,
        description=payload.description.strip(),
        evidence=[item.model_dump(exclude_none=True) for item in payload.evidence],
        status="pending",
    )
    db.add(report)
    db.flush()
    db.add(AuditEvent(
        actor_id=reporter.id,
        action="report.created",
        resource_type="report",
        resource_id=report.id,
        event_metadata={
            "target_type": "listing" if listing is not None else "seller",
            "target_id": listing.id if listing is not None else seller.id,
            "reason": report.reason,
        },
    ))
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "status": report.status,
        "created_at": report.created_at,
    }


@router.get("/my")
def my_reports(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    reporter: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.scalars(
        select(Report).where(Report.reporter_user_id == reporter.id)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .offset(offset).limit(limit)
    ).all()
    return [{
        "id": row.id,
        "listing_id": row.listing_id,
        "seller_id": row.seller_id,
        "reason": row.reason,
        "description": row.description,
        "status": row.status,
        "review_note": row.review_note,
        "created_at": row.created_at,
        "reviewed_at": row.reviewed_at,
    } for row in rows]
