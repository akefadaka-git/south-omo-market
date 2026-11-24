from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, bindparam, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.governance import require_permission
from app.policy_engine import evaluate_policy
from app.models import User

router = APIRouter(prefix="/employment")


class PaymentVerification(BaseModel):
    verification_note: str = Field(min_length=3, max_length=1000)


class OwnerProviderCreate(BaseModel):
    user_id: str
    business_code: str = Field(min_length=2, max_length=80)
    legal_name: str = Field(min_length=2, max_length=200)
    display_name: str = Field(min_length=2, max_length=200)
    business_type: str = Field(min_length=2, max_length=60)


@router.post("/admin/providers", status_code=201)
def create_employment_provider_record(
    payload: OwnerProviderCreate,
    owner: User = Depends(require_permission("employment.provider.verify")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if db.execute(text("SELECT id FROM users WHERE id = :id"), {"id": payload.user_id}).scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Provider contact account not found")
    if db.execute(text("SELECT id FROM business_profiles WHERE business_code = :code"), {"code": payload.business_code}).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Business code already exists")
    business_id, provider_id = str(uuid4()), str(uuid4())
    db.execute(text("""
        INSERT INTO business_profiles
            (id, business_code, legal_name, display_name, business_type, verification_status, is_active)
        VALUES (:id, :code, :legal, :display, :kind, 'pending', TRUE)
    """), {"id": business_id, "code": payload.business_code, "legal": payload.legal_name,
           "display": payload.display_name, "kind": payload.business_type})
    db.execute(text("""
        INSERT INTO business_memberships
            (id, business_id, user_id, membership_role, status)
        VALUES (:id, :business, :user, 'owner', 'active')
    """), {"id": str(uuid4()), "business": business_id, "user": payload.user_id})
    db.execute(text("""
        INSERT INTO employment_providers (id, business_id, verification_status)
        VALUES (:id, :business, 'pending')
    """), {"id": provider_id, "business": business_id})
    db.execute(text("""
        INSERT INTO employment_events
            (id, actor_id, event_type, resource_type, resource_id, event_metadata)
        VALUES (:id, :actor, 'employment.provider.created',
                'employment_provider', :resource, :metadata)
    """).bindparams(bindparam("metadata", type_=JSON)), {
        "id": str(uuid4()), "actor": owner.id, "resource": provider_id,
        "metadata": {"business_id": business_id, "contact_user_id": payload.user_id},
    })
    db.commit()
    return {"provider_id": provider_id, "business_id": business_id, "verification_status": "pending"}


@router.post("/admin/providers/{provider_id}/verify")
def verify_employment_provider(
    provider_id: str,
    owner: User = Depends(require_permission("employment.provider.verify")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT ep.id, ep.business_id, ep.verification_status
        FROM employment_providers ep WHERE ep.id = :id FOR UPDATE
    """), {"id": provider_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Employment provider not found")
    if row["verification_status"] == "verified":
        return {"provider_id": provider_id, "verification_status": "verified"}
    db.execute(text("""
        UPDATE employment_providers
        SET verification_status = 'verified', verified_at = CURRENT_TIMESTAMP, verified_by = :owner
        WHERE id = :id
    """), {"owner": owner.id, "id": provider_id})
    db.execute(text("""
        UPDATE business_profiles SET verification_status = 'verified'
        WHERE id = :business
    """), {"business": row["business_id"]})
    db.execute(text("""
        INSERT INTO employment_events
            (id, actor_id, event_type, resource_type, resource_id, event_metadata)
        VALUES (:id, :actor, 'employment.provider.verified',
                'employment_provider', :resource, '{}')
    """), {"id": str(uuid4()), "actor": owner.id, "resource": provider_id})
    db.commit()
    return {"provider_id": provider_id, "verification_status": "verified"}


class OwnerAdvertisementCreate(BaseModel):
    provider_id: str
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    occupation_code: str = Field(min_length=2, max_length=80)
    location_code: str = Field(min_length=2, max_length=80)
    employment_type: str = Field(min_length=2, max_length=40)
    requirements: list[dict[str, object]] = Field(default_factory=list)
    agreed_price_minor: int = Field(gt=0)
    duration_days: int = Field(gt=0, le=365)
    terms_version: str = Field(min_length=1, max_length=40)


class AgreementAcceptance(BaseModel):
    acceptance_evidence: str = Field(min_length=3, max_length=2000)


class PaymentSubmission(BaseModel):
    amount_minor: int = Field(gt=0)
    currency: str = Field(default="ETB", min_length=3, max_length=3)
    payment_method: str = Field(min_length=2, max_length=40)
    evidence_ref: str = Field(min_length=3, max_length=2000)
    external_reference: str | None = Field(default=None, max_length=160)


@router.post("/admin/advertisements", status_code=201)
def create_owner_managed_advertisement(
    payload: OwnerAdvertisementCreate,
    owner: User = Depends(require_permission("employment.advertisement.manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    provider_status = db.execute(text("""
        SELECT verification_status FROM employment_providers WHERE id = :provider_id
    """), {"provider_id": payload.provider_id}).scalar_one_or_none()
    if provider_status is None:
        raise HTTPException(status_code=404, detail="Employment provider not found")
    if provider_status != "verified":
        raise HTTPException(status_code=409, detail="Provider must be verified before an ad is prepared")
    opportunity_id, agreement_id, advertisement_id = str(uuid4()), str(uuid4()), str(uuid4())
    db.execute(text("""
        INSERT INTO employment_opportunities
            (id, provider_id, title, description, occupation_code, location_code,
             employment_type, requirements, status)
        VALUES (:id, :provider, :title, :description, :occupation, :location,
                :employment_type, :requirements, 'draft')
    """).bindparams(bindparam("requirements", type_=JSON)), {
        "id": opportunity_id, "provider": payload.provider_id,
        "title": payload.title, "description": payload.description,
        "occupation": payload.occupation_code, "location": payload.location_code,
        "employment_type": payload.employment_type, "requirements": payload.requirements,
    })
    db.execute(text("""
        INSERT INTO advertising_agreements
            (id, provider_id, opportunity_id, terms_version, agreed_price_minor,
             currency, duration_days, status)
        VALUES (:id, :provider, :opportunity, :terms, :price, 'ETB', :duration, 'pending')
    """), {
        "id": agreement_id, "provider": payload.provider_id,
        "opportunity": opportunity_id, "terms": payload.terms_version,
        "price": payload.agreed_price_minor, "duration": payload.duration_days,
    })
    db.execute(text("""
        INSERT INTO employment_advertisements
            (id, opportunity_id, agreement_id, status)
        VALUES (:id, :opportunity, :agreement, 'pending_owner')
    """), {"id": advertisement_id, "opportunity": opportunity_id, "agreement": agreement_id})
    db.execute(text("""
        INSERT INTO employment_events
            (id, actor_id, event_type, resource_type, resource_id, event_metadata)
        VALUES (:id, :actor, 'employment.advertisement.prepared',
                'employment_advertisement', :resource, :metadata)
    """).bindparams(bindparam("metadata", type_=JSON)), {
        "id": str(uuid4()), "actor": owner.id, "resource": advertisement_id,
        "metadata": {"provider_id": payload.provider_id, "agreement_id": agreement_id},
    })
    db.commit()
    return {"advertisement_id": advertisement_id, "agreement_id": agreement_id, "status": "pending_provider_acceptance"}


@router.post("/advertising-agreements/{agreement_id}/accept")
def accept_advertising_agreement(
    agreement_id: str,
    payload: AgreementAcceptance,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT ag.id, ag.status, ep.verification_status
        FROM advertising_agreements ag
        JOIN employment_providers ep ON ep.id = ag.provider_id
        JOIN business_memberships bm ON bm.business_id = ep.business_id
        WHERE ag.id = :agreement_id AND bm.user_id = :user_id
          AND bm.status = 'active'
        FOR UPDATE OF ag
    """), {"agreement_id": agreement_id, "user_id": user.id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Agreement not found for this provider account")
    if row["verification_status"] != "verified":
        raise HTTPException(status_code=403, detail="Provider is not verified")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail="Agreement is not awaiting acceptance")
    db.execute(text("""
        UPDATE advertising_agreements
        SET status = 'accepted', provider_accepted_at = CURRENT_TIMESTAMP,
            provider_acceptance_evidence = :evidence
        WHERE id = :agreement_id
    """), {"evidence": payload.acceptance_evidence, "agreement_id": agreement_id})
    db.commit()
    return {"agreement_id": agreement_id, "status": "accepted"}


@router.post("/advertising-agreements/{agreement_id}/payments", status_code=201)
def submit_advertising_payment_evidence(
    agreement_id: str,
    payload: PaymentSubmission,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT ag.id, ag.status, ag.currency, ep.verification_status
        FROM advertising_agreements ag
        JOIN employment_providers ep ON ep.id = ag.provider_id
        JOIN business_memberships bm ON bm.business_id = ep.business_id
        WHERE ag.id = :agreement_id AND bm.user_id = :user_id
          AND bm.status = 'active'
        FOR UPDATE OF ag
    """), {"agreement_id": agreement_id, "user_id": user.id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Agreement not found for this provider account")
    if row["verification_status"] != "verified" or row["status"] != "accepted":
        raise HTTPException(status_code=409, detail="Verified provider and accepted agreement are required")
    if payload.currency != row["currency"]:
        raise HTTPException(status_code=422, detail="Payment currency does not match the agreement")
    payment_id = str(uuid4())
    db.execute(text("""
        INSERT INTO advertising_payments
            (id, agreement_id, amount_minor, currency, payment_method,
             external_reference, evidence_ref, status)
        VALUES (:id, :agreement, :amount, :currency, :method, :external, :evidence, 'submitted')
    """), {
        "id": payment_id, "agreement": agreement_id, "amount": payload.amount_minor,
        "currency": payload.currency, "method": payload.payment_method,
        "external": payload.external_reference, "evidence": payload.evidence_ref,
    })
    db.commit()
    return {"payment_id": payment_id, "status": "submitted_for_owner_verification"}


class CandidateConsentRequest(BaseModel):
    purpose: str = Field(min_length=3, max_length=120)
    consent_version: str = Field(min_length=1, max_length=40)


@router.post("/opportunities/{opportunity_id}/apply", status_code=201)
def apply_to_published_opportunity(
    opportunity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    profile_id = db.execute(text("""
        SELECT id FROM job_seeker_profiles WHERE user_id = :user_id
    """), {"user_id": user.id}).scalar_one_or_none()
    if profile_id is None:
        raise HTTPException(status_code=409, detail="Create a private job-seeker profile before applying")
    visible = db.execute(text("""
        SELECT o.id FROM employment_opportunities o
        JOIN employment_advertisements a ON a.opportunity_id = o.id
        WHERE o.id = :opportunity_id AND o.status = 'open'
          AND a.status = 'published' AND a.expires_at > CURRENT_TIMESTAMP
    """), {"opportunity_id": opportunity_id}).scalar_one_or_none()
    if visible is None:
        raise HTTPException(status_code=404, detail="Published employment opportunity not found")
    application_id = str(uuid4())
    try:
        db.execute(text("""
            INSERT INTO employment_applications (id, opportunity_id, job_seeker_id, status)
            VALUES (:id, :opportunity, :profile, 'submitted')
            ON CONFLICT (opportunity_id, job_seeker_id) DO NOTHING
        """), {"id": application_id, "opportunity": opportunity_id, "profile": profile_id})
        existing = db.execute(text("""
            SELECT id FROM employment_applications
            WHERE opportunity_id = :opportunity AND job_seeker_id = :profile
        """), {"opportunity": opportunity_id, "profile": profile_id}).scalar_one()
        db.commit()
        return {"application_id": existing, "status": "submitted"}
    except Exception:
        db.rollback()
        raise


@router.post("/applications/{application_id}/consent")
def grant_candidate_sharing_consent(
    application_id: str,
    payload: CandidateConsentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT app.id, app.job_seeker_id, o.provider_id
        FROM employment_applications app
        JOIN job_seeker_profiles jsp ON jsp.id = app.job_seeker_id
        JOIN employment_opportunities o ON o.id = app.opportunity_id
        WHERE app.id = :application AND jsp.user_id = :user_id
        FOR UPDATE OF app
    """), {"application": application_id, "user_id": user.id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    consent_id = db.execute(text("""
        SELECT id FROM candidate_consents
        WHERE job_seeker_id = :profile AND provider_id = :provider
          AND purpose = :purpose AND withdrawn_at IS NULL
    """), {"profile": row["job_seeker_id"], "provider": row["provider_id"], "purpose": payload.purpose}).scalar_one_or_none()
    if consent_id is None:
        consent_id = str(uuid4())
        db.execute(text("""
            INSERT INTO candidate_consents
                (id, job_seeker_id, provider_id, purpose, consent_version, granted_at)
            VALUES (:id, :profile, :provider, :purpose, :version, CURRENT_TIMESTAMP)
        """), {"id": consent_id, "profile": row["job_seeker_id"], "provider": row["provider_id"],
               "purpose": payload.purpose, "version": payload.consent_version})
    db.commit()
    return {"consent_id": consent_id, "status": "granted"}


@router.get("/providers/{provider_id}/consented-candidates")
def list_consented_candidates(
    provider_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    membership = db.execute(text("""
        SELECT ep.id FROM employment_providers ep
        JOIN business_memberships bm ON bm.business_id = ep.business_id
        WHERE ep.id = :provider AND ep.verification_status = 'verified'
          AND bm.user_id = :user_id AND bm.status = 'active'
    """), {"provider": provider_id, "user_id": user.id}).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="Verified provider membership is required")
    rows = db.execute(text("""
        SELECT DISTINCT jsp.id AS profile_id, jsp.skills, jsp.experience,
               jsp.qualifications, jsp.preferred_occupations,
               jsp.preferred_location_codes, jsp.availability, app.id AS application_id
        FROM candidate_consents cc
        JOIN job_seeker_profiles jsp ON jsp.id = cc.job_seeker_id
        JOIN employment_applications app ON app.job_seeker_id = jsp.id
        JOIN employment_opportunities o ON o.id = app.opportunity_id
        WHERE cc.provider_id = :provider AND cc.withdrawn_at IS NULL
          AND o.provider_id = cc.provider_id
          AND jsp.visibility IN ('private', 'consented_employers')
        ORDER BY app.created_at DESC
        LIMIT 100
    """), {"provider": provider_id}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/admin/applications/{application_id}/refer", status_code=201)
def create_human_review_candidate_referral(
    application_id: str,
    user: User = Depends(require_permission("employment.candidate.refer")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.execute(text("""
        SELECT app.id, o.provider_id, app.job_seeker_id
        FROM employment_applications app
        JOIN employment_opportunities o ON o.id = app.opportunity_id
        JOIN candidate_consents cc ON cc.job_seeker_id = app.job_seeker_id
            AND cc.provider_id = o.provider_id AND cc.withdrawn_at IS NULL
        WHERE app.id = :application
        LIMIT 1
    """), {"application": application_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=409, detail="Active candidate consent is required before referral")
    referral_id = str(uuid4())
    db.execute(text("""
        INSERT INTO candidate_referrals
            (id, application_id, provider_id, referred_by, decision, matching_metadata)
        VALUES (:id, :application, :provider, :actor, 'human_review', '{}')
    """), {"id": referral_id, "application": application_id,
           "provider": row["provider_id"], "actor": user.id})
    db.commit()
    return {"referral_id": referral_id, "decision": "human_review"}


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
    db.execute(text("SELECT id FROM employment_advertisements WHERE id = :ad_id FOR UPDATE"), {"ad_id": advertisement_id})
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
    if not evaluate_policy(
        db,
        subject="role:owner",
        action="employment.advertisement.publish",
        resource="employment_advertisements",
        facts={
            "provider_verified": row["provider_status"] == "verified",
            "agreement_accepted": row["agreement_status"] == "accepted",
            "payment_verified": int(row["verified_total"]) >= int(row["agreed_price_minor"]),
        },
    ):
        raise HTTPException(status_code=403, detail="Active policy pack denied advertisement publication")
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
