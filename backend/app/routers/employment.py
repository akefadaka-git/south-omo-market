from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, bindparam, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.governance import require_permission
from app.models import User

router = APIRouter(prefix="/employment")


class PaymentVerification(BaseModel):
    verification_note: str = Field(min_length=3, max_length=1000)


@router.get("/advertisements")
def list_published_employment_advertisements(
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.execute(text("""
        SELECT a.id, o.title, o.description, o.occupation_code, o.location_code,
               o.employment_type, a.published_at, a.expires_at
        FROM employment_advertisements a
        JOIN employment_opportunities o ON o.id = a.opportunity_id
        WHERE a.status = 'published' AND a.expires_at > CURRENT_TIMESTAMP
          AND o.status = 'open'
        ORDER BY a.published_at DESC, a.id
        LIMIT 100
    """)).mappings().all()
    return [dict(row) for row in rows]


@router.post("/admin/advertisements/{advertisement_id}/payments/{payment_id}/verify")
def verify_advertising_payment(
    advertisement_id: str,
    payment_id: str,
    payload: PaymentVerification,
    owner: User = Depends(require_permission("employment.payment.verify")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT p.id, p.agreement_id, p.status, p.evidence_ref, ag.agreed_price_minor,
               ag.currency, ag.status AS agreement_status, a.agreement_id AS ad_agreement_id
        FROM advertising_payments p
        JOIN advertising_agreements ag ON ag.id = p.agreement_id
        JOIN employment_advertisements a ON a.agreement_id = ag.id
        WHERE a.id = :ad_id AND p.id = :payment_id
        FOR UPDATE
    """), {"ad_id": advertisement_id, "payment_id": payment_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Advertising payment not found")
    if row["status"] == "verified":
        return {"payment_id": payment_id, "status": "verified"}
    if row["status"] != "submitted" or not row["evidence_ref"]:
        raise HTTPException(status_code=409, detail="Payment evidence is not eligible for verification")
    db.execute(text("""
        UPDATE advertising_payments
        SET status = 'verified', verified_by = :owner_id,
            verified_at = CURRENT_TIMESTAMP
        WHERE id = :payment_id
    """), {"owner_id": owner.id, "payment_id": payment_id})
    db.execute(text("""
        INSERT INTO employment_events
            (id, actor_id, event_type, resource_type, resource_id, event_metadata)
        VALUES (:id, :actor, 'advertising.payment.verified',
                'advertising_payment', :resource, :metadata)
    """).bindparams(bindparam("metadata", type_=JSON)), {
        "id": str(uuid4()), "actor": owner.id, "resource": payment_id,
        "metadata": {"advertisement_id": advertisement_id, "verification_note": payload.verification_note},
    })
    db.commit()
    return {"payment_id": payment_id, "status": "verified"}


@router.post("/admin/advertisements/{advertisement_id}/publish")
def publish_employment_advertisement(
    advertisement_id: str,
    owner: User = Depends(require_permission("employment.advertisement.publish")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT a.id, a.status AS ad_status, a.opportunity_id, ag.id AS agreement_id,
               ag.agreed_price_minor, ag.duration_days, ag.provider_accepted_at,
               ag.status AS agreement_status, ep.verification_status AS provider_status,
               COALESCE(SUM(CASE WHEN p.status = 'verified' AND p.currency = ag.currency
                                 THEN p.amount_minor ELSE 0 END), 0) AS verified_total
        FROM employment_advertisements a
        JOIN advertising_agreements ag ON ag.id = a.agreement_id
        JOIN employment_opportunities o ON o.id = a.opportunity_id
        JOIN employment_providers ep ON ep.id = o.provider_id
        LEFT JOIN advertising_payments p ON p.agreement_id = ag.id
        WHERE a.id = :ad_id
        GROUP BY a.id, ag.id, ep.verification_status
        FOR UPDATE OF a
    """), {"ad_id": advertisement_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Employment advertisement not found")
    if row["ad_status"] == "published":
        return {"advertisement_id": advertisement_id, "status": "published"}
    if row["ad_status"] != "pending_owner":
        raise HTTPException(status_code=409, detail="Advertisement is not awaiting Owner publication")
    if row["provider_status"] != "verified":
        raise HTTPException(status_code=409, detail="Employment provider is not verified")
    if row["agreement_status"] != "accepted" or row["provider_accepted_at"] is None:
        raise HTTPException(status_code=409, detail="Provider has not accepted the advertising agreement")
    if int(row["verified_total"]) < int(row["agreed_price_minor"]):
        raise HTTPException(status_code=409, detail="Verified payment does not cover the agreed advertising price")
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=int(row["duration_days"]))
    db.execute(text("""
        UPDATE employment_advertisements
        SET status = 'published', published_by = :owner_id,
            published_at = :published_at, expires_at = :expires_at
        WHERE id = :ad_id
    """), {"owner_id": owner.id, "published_at": now, "expires_at": expires, "ad_id": advertisement_id})
    db.execute(text("""
        UPDATE employment_opportunities SET status = 'open' WHERE id = :opportunity_id
    """), {"opportunity_id": row["opportunity_id"]})
    db.execute(text("""
        INSERT INTO employment_events
            (id, actor_id, event_type, resource_type, resource_id, event_metadata)
        VALUES (:id, :actor, 'employment.advertisement.published',
                'employment_advertisement', :resource, :metadata)
    """).bindparams(bindparam("metadata", type_=JSON)), {
        "id": str(uuid4()), "actor": owner.id, "resource": advertisement_id,
        "metadata": {"agreement_id": row["agreement_id"], "verified_payment_minor": int(row["verified_total"])},
    })
    db.commit()
    return {"advertisement_id": advertisement_id, "status": "published"}


@router.put("/job-seeker/profile")
def upsert_private_job_seeker_profile(
    payload: dict[str, object],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    allowed = {
        "skills", "experience", "qualifications", "preferred_occupations",
        "preferred_location_codes", "availability", "contact_preferences",
    }
    if set(payload) - allowed:
        raise HTTPException(status_code=422, detail="Unsupported job-seeker profile fields")
    for key in ("skills", "experience", "qualifications", "preferred_occupations", "preferred_location_codes"):
        if key in payload and not isinstance(payload[key], list):
            raise HTTPException(status_code=422, detail=f"{key} must be a list")
    if "contact_preferences" in payload and not isinstance(payload["contact_preferences"], dict):
        raise HTTPException(status_code=422, detail="contact_preferences must be an object")
    existing = db.execute(text("""
        SELECT id FROM job_seeker_profiles WHERE user_id = :user_id
    """), {"user_id": user.id}).scalar_one_or_none()
    profile_id = existing or str(uuid4())
    profile_statement = text("""
        INSERT INTO job_seeker_profiles
            (id, user_id, skills, experience, qualifications, preferred_occupations,
             preferred_location_codes, availability, contact_preferences, visibility)
        VALUES (:id, :user_id, :skills, :experience, :qualifications, :occupations,
                :locations, :availability, :contacts, 'private')
        ON CONFLICT (user_id) DO UPDATE SET
            skills = EXCLUDED.skills, experience = EXCLUDED.experience,
            qualifications = EXCLUDED.qualifications,
            preferred_occupations = EXCLUDED.preferred_occupations,
            preferred_location_codes = EXCLUDED.preferred_location_codes,
            availability = EXCLUDED.availability,
            contact_preferences = EXCLUDED.contact_preferences
    """).bindparams(
        bindparam("skills", type_=JSON), bindparam("experience", type_=JSON),
        bindparam("qualifications", type_=JSON), bindparam("occupations", type_=JSON),
        bindparam("locations", type_=JSON), bindparam("contacts", type_=JSON),
    )
    db.execute(profile_statement, {
        "id": profile_id, "user_id": user.id,
        "skills": payload.get("skills", []), "experience": payload.get("experience", []),
        "qualifications": payload.get("qualifications", []),
        "occupations": payload.get("preferred_occupations", []),
        "locations": payload.get("preferred_location_codes", []),
        "availability": payload.get("availability"),
        "contacts": payload.get("contact_preferences", {}),
    })
    db.commit()
    return {"profile_id": profile_id, "visibility": "private"}
