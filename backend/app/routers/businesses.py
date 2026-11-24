from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, bindparam, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.governance import require_business_permission, require_permission
from app.models import User

router = APIRouter(prefix="/businesses")
ASSIGNABLE_ROLES = {"administrator", "manager", "staff", "finance", "viewer"}


class MembershipInvite(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    membership_role: str = Field(min_length=1, max_length=40)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class VerificationDecision(BaseModel):
    status: str
    notes: str = Field(min_length=3, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


def _event(db, business_id, membership_id, actor_id, event_type, metadata):
    db.execute(text("""
        INSERT INTO business_membership_events
        (id,business_id,membership_id,actor_id,event_type,event_metadata)
        VALUES (:id,:business,:membership,:actor,:event,:metadata)
    """).bindparams(bindparam("metadata", type_=JSON)), {
        "id":str(uuid4()), "business":business_id, "membership":membership_id,
        "actor":actor_id, "event":event_type, "metadata":metadata,
    })


@router.get("/{business_id}")
def get_business(business_id: str,
    user: User = Depends(require_business_permission("business.profile.read")),
    db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT id,business_code,legal_name,display_name,business_type,verification_status,
        is_active,registration_number,registered_address,contact_email,contact_phone,
        created_at,updated_at FROM business_profiles WHERE id=:id
    """), {"id":business_id}).mappings().first()
    if row is None:
        raise HTTPException(404, "Business not found")
    return dict(row)


@router.get("/{business_id}/memberships")
def list_members(business_id: str,
    user: User = Depends(require_business_permission("business.member.manage")),
    db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT bm.id,bm.user_id,u.display_name,bm.membership_role,bm.status,
        bm.invited_by,bm.invited_at,bm.accepted_at,bm.expires_at,bm.revoked_by,
        bm.revoked_at,bm.created_at,bm.updated_at
        FROM business_memberships bm JOIN users u ON u.id=bm.user_id
        WHERE bm.business_id=:business ORDER BY bm.created_at,bm.id
    """), {"business":business_id}).mappings().all()
    return [dict(r) for r in rows]


@router.post("/{business_id}/memberships", status_code=201)
def invite_member(business_id: str, payload: MembershipInvite,
    user: User = Depends(require_business_permission("business.member.manage")),
    db: Session = Depends(get_db)):
    actor_role = db.execute(text("""
        SELECT membership_role FROM business_memberships
        WHERE business_id=:b AND user_id=:u AND status='active'
          AND (expires_at IS NULL OR expires_at>CURRENT_TIMESTAMP)
    """), {"b":business_id,"u":user.id}).scalar_one_or_none()
    if actor_role not in {"owner","administrator"}:
        raise HTTPException(403,"Only business owners or administrators may invite members")
    if payload.membership_role not in ASSIGNABLE_ROLES:
        raise HTTPException(422,"Unsupported role; business ownership cannot be delegated")
    if actor_role == "administrator" and payload.membership_role == "administrator":
        raise HTTPException(403,"Administrators cannot appoint other administrators")
    if db.execute(text("SELECT id FROM users WHERE id=:id AND is_active=TRUE AND is_suspended=FALSE"),
                  {"id":payload.user_id}).scalar_one_or_none() is None:
        raise HTTPException(404,"Invitee account not found or inactive")
    if db.execute(text("""
        SELECT id FROM business_memberships WHERE business_id=:b AND user_id=:u
        AND status IN ('invited','pending','active','suspended')
    """), {"b":business_id,"u":payload.user_id}).scalar_one_or_none():
        raise HTTPException(409,"User already has a current membership or invitation")
    mid = str(uuid4())
    expiry = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    db.execute(text("""
        INSERT INTO business_memberships
        (id,business_id,user_id,membership_role,status,invited_by,invited_at,expires_at)
        VALUES (:id,:b,:u,:role,'invited',:actor,CURRENT_TIMESTAMP,:expiry)
    """), {"id":mid,"b":business_id,"u":payload.user_id,"role":payload.membership_role,
           "actor":user.id,"expiry":expiry})
    _event(db,business_id,mid,user.id,"business.membership.invited",
           {"invitee_user_id":payload.user_id,"membership_role":payload.membership_role,
            "expires_at":expiry.isoformat()})
    db.commit()
    return {"membership_id":mid,"status":"invited"}


@router.post("/{business_id}/memberships/{membership_id}/accept")
def accept_invite(business_id: str, membership_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT bm.user_id,bm.status,bm.expires_at,bp.is_active
        FROM business_memberships bm JOIN business_profiles bp ON bp.id=bm.business_id
        WHERE bm.id=:m AND bm.business_id=:b
    """), {"m":membership_id,"b":business_id}).mappings().first()
    if row is None:
        raise HTTPException(404,"Invitation not found")
    if row["user_id"] != user.id:
        raise HTTPException(403,"Only the invited account may accept this invitation")
    if row["status"] != "invited":
        raise HTTPException(409,"Invitation is no longer pending")
    expiry = row["expires_at"]
    if expiry is not None:
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            db.execute(text("UPDATE business_memberships SET status='expired',updated_at=CURRENT_TIMESTAMP WHERE id=:m"), {"m":membership_id})
            _event(db,business_id,membership_id,user.id,"business.membership.expired",{})
            db.commit()
            raise HTTPException(410,"Invitation expired")
    if not row["is_active"]:
        raise HTTPException(409,"Business is inactive")
    db.execute(text("""
        UPDATE business_memberships SET status='active',accepted_at=CURRENT_TIMESTAMP,
        updated_at=CURRENT_TIMESTAMP WHERE id=:m AND status='invited'
    """), {"m":membership_id})
    _event(db,business_id,membership_id,user.id,"business.membership.accepted",{})
    db.commit()
    return {"membership_id":membership_id,"status":"active"}


@router.delete("/{business_id}/memberships/{membership_id}")
def revoke_member(business_id: str, membership_id: str,
    user: User = Depends(require_business_permission("business.member.manage")),
    db: Session = Depends(get_db)):
    actor_role = db.execute(text("""
        SELECT membership_role FROM business_memberships
        WHERE business_id=:b AND user_id=:u AND status='active'
    """), {"b":business_id,"u":user.id}).scalar_one_or_none()
    row = db.execute(text("""
        SELECT user_id,membership_role,status FROM business_memberships
        WHERE id=:m AND business_id=:b
    """), {"m":membership_id,"b":business_id}).mappings().first()
    if row is None:
        raise HTTPException(404,"Membership not found")
    if actor_role not in {"owner","administrator"}:
        raise HTTPException(403,"Only business owners or administrators may revoke membership")
    if row["membership_role"] == "owner":
        raise HTTPException(409,"Business owner membership cannot be revoked here")
    if actor_role == "administrator" and row["membership_role"] == "administrator":
        raise HTTPException(403,"Administrators cannot revoke another administrator")
    if row["status"] in {"revoked","rejected","expired"}:
        raise HTTPException(409,"Membership is already closed")
    db.execute(text("""
        UPDATE business_memberships SET status='revoked',revoked_by=:actor,
        revoked_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=:m
    """), {"actor":user.id,"m":membership_id})
    _event(db,business_id,membership_id,user.id,"business.membership.revoked",
           {"member_user_id":row["user_id"],"previous_status":row["status"]})
    db.commit()
    return {"membership_id":membership_id,"status":"revoked"}


@router.post("/admin/{business_id}/verification")
def verify_business(business_id: str, payload: VerificationDecision,
    owner: User = Depends(require_permission("business.verification.manage")),
    db: Session = Depends(get_db)):
    if payload.status not in {"verified","rejected","suspended"}:
        raise HTTPException(422,"Unsupported verification decision")
    row = db.execute(text("SELECT verification_status FROM business_profiles WHERE id=:id"),
                     {"id":business_id}).mappings().first()
    if row is None:
        raise HTTPException(404,"Business not found")
    previous = row["verification_status"]
    transitions = {"pending":{"verified","rejected","suspended"},
                   "verified":{"suspended"},"suspended":{"verified"},"rejected":set()}
    if payload.status not in transitions.get(previous,set()):
        raise HTTPException(409,f"Cannot change verification from {previous} to {payload.status}")
    db.execute(text("""
        UPDATE business_profiles SET verification_status=:status,verification_notes=:notes,
        verification_evidence=:evidence,verified_by=:actor,
        verified_at=CASE WHEN :status='verified' THEN CURRENT_TIMESTAMP ELSE verified_at END,
        suspended_at=CASE WHEN :status='suspended' THEN CURRENT_TIMESTAMP
                          WHEN :status='verified' THEN NULL ELSE suspended_at END,
        is_active=CASE WHEN :status='verified' THEN TRUE
                       WHEN :status IN ('rejected','suspended') THEN FALSE ELSE is_active END,
        updated_at=CURRENT_TIMESTAMP WHERE id=:id
    """).bindparams(bindparam("evidence",type_=JSON)), {
        "status":payload.status,"notes":payload.notes,"evidence":payload.evidence_refs,
        "actor":owner.id,"id":business_id})
    db.execute(text("""
        INSERT INTO business_verification_events
        (id,business_id,actor_id,previous_status,new_status,evidence_refs,notes)
        VALUES (:id,:b,:actor,:previous,:new,:evidence,:notes)
    """).bindparams(bindparam("evidence",type_=JSON)), {
        "id":str(uuid4()),"b":business_id,"actor":owner.id,"previous":previous,
        "new":payload.status,"evidence":payload.evidence_refs,"notes":payload.notes})
    if payload.status == "verified":
        owners = db.execute(text("""
            SELECT id FROM business_memberships
            WHERE business_id=:b AND membership_role='owner' AND status='pending'
        """), {"b":business_id}).scalars().all()
        for mid in owners:
            db.execute(text("""
                UPDATE business_memberships SET status='active',
                accepted_at=COALESCE(accepted_at,CURRENT_TIMESTAMP),updated_at=CURRENT_TIMESTAMP
                WHERE id=:m
            """), {"m":mid})
            _event(db,business_id,mid,owner.id,"business.membership.activated_by_verification",
                   {"verification_status":"verified"})
    db.commit()
    return {"business_id":business_id,"verification_status":payload.status}
