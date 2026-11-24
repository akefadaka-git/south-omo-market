from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.governance import require_business_permission, require_permission
from app.routers.businesses import MembershipInvite, VerificationDecision, invite_member, accept_invite, revoke_member, verify_business


def db_fixture():
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.exec_driver_sql("CREATE TABLE users (id TEXT PRIMARY KEY, display_name TEXT, is_active BOOLEAN, is_suspended BOOLEAN)")
        c.exec_driver_sql("""CREATE TABLE business_profiles (
            id TEXT PRIMARY KEY,business_code TEXT,legal_name TEXT,display_name TEXT,business_type TEXT,
            verification_status TEXT,is_active BOOLEAN,registration_number TEXT,registered_address TEXT,
            contact_email TEXT,contact_phone TEXT,verification_notes TEXT,verification_evidence JSON,
            verified_by TEXT,verified_at DATETIME,suspended_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        c.exec_driver_sql("""CREATE TABLE business_memberships (
            id TEXT PRIMARY KEY,business_id TEXT,user_id TEXT,membership_role TEXT,status TEXT,
            invited_by TEXT,invited_at DATETIME,accepted_at DATETIME,revoked_by TEXT,revoked_at DATETIME,
            expires_at DATETIME,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        c.exec_driver_sql("CREATE TABLE business_role_permissions (id TEXT,membership_role TEXT,permission_code TEXT)")
        c.exec_driver_sql("""CREATE TABLE business_membership_events (
            id TEXT,business_id TEXT,membership_id TEXT,actor_id TEXT,event_type TEXT,event_metadata JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        c.exec_driver_sql("""CREATE TABLE business_verification_events (
            id TEXT,business_id TEXT,actor_id TEXT,previous_status TEXT,new_status TEXT,evidence_refs JSON,
            notes TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        c.exec_driver_sql("CREATE TABLE roles (id TEXT,code TEXT)")
        c.exec_driver_sql("CREATE TABLE permissions (id TEXT,code TEXT)")
        c.exec_driver_sql("CREATE TABLE role_permissions (role_id TEXT,permission_id TEXT)")
        c.exec_driver_sql("CREATE TABLE user_roles (user_id TEXT,role_id TEXT,expires_at DATETIME)")
        c.exec_driver_sql("CREATE TABLE user_permissions (user_id TEXT,permission_id TEXT,granted BOOLEAN)")
    return engine


def test_business_permission_is_scoped_to_business_and_active_membership():
    engine = db_fixture()
    try:
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO business_profiles (id,business_code,legal_name,display_name,business_type,verification_status,is_active) VALUES ('b1','B1','B1','B1','retail','verified',1),('b2','B2','B2','B2','retail','verified',1)")
            c.exec_driver_sql("INSERT INTO business_memberships (id,business_id,user_id,membership_role,status) VALUES ('m1','b1','u1','manager','active'),('m2','b2','u1','manager','revoked')")
            c.exec_driver_sql("INSERT INTO business_role_permissions VALUES ('p1','manager','business.profile.read')")
        with Session(engine) as db:
            dep = require_business_permission("business.profile.read")
            assert dep(business_id="b1",user=SimpleNamespace(id="u1"),db=db).id == "u1"
            with pytest.raises(HTTPException) as err:
                dep(business_id="b2",user=SimpleNamespace(id="u1"),db=db)
            assert err.value.status_code == 403
    finally:
        engine.dispose()


def test_invitation_acceptance_revocation_and_audit_trail():
    engine = db_fixture()
    try:
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO users VALUES ('owner','Owner',1,0),('invitee','Invitee',1,0),('attacker','Attacker',1,0)")
            c.exec_driver_sql("INSERT INTO business_profiles (id,business_code,legal_name,display_name,business_type,verification_status,is_active) VALUES ('b1','B1','B1','B1','retail','verified',1)")
            c.exec_driver_sql("INSERT INTO business_memberships (id,business_id,user_id,membership_role,status) VALUES ('om','b1','owner','owner','active')")
            c.exec_driver_sql("INSERT INTO business_role_permissions VALUES ('p1','owner','business.member.manage')")
        with Session(engine) as db:
            owner=SimpleNamespace(id="owner")
            invited=invite_member("b1",MembershipInvite(user_id="invitee",membership_role="viewer"),user=owner,db=db)
            mid=invited["membership_id"]
            with pytest.raises(HTTPException) as err:
                accept_invite("b1",mid,user=SimpleNamespace(id="attacker"),db=db)
            assert err.value.status_code == 403
            assert accept_invite("b1",mid,user=SimpleNamespace(id="invitee"),db=db)["status"] == "active"
            assert revoke_member("b1",mid,user=owner,db=db)["status"] == "revoked"
            assert db.execute(text("SELECT status,revoked_by FROM business_memberships WHERE id=:id"),{"id":mid}).one() == ("revoked","owner")
            events=db.execute(text("SELECT event_type FROM business_membership_events WHERE membership_id=:id"),{"id":mid}).scalars().all()
            assert set(events) == {"business.membership.invited","business.membership.accepted","business.membership.revoked"}
    finally:
        engine.dispose()


def test_business_admin_cannot_grant_owner_or_peer_admin_role():
    engine=db_fixture()
    try:
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO users VALUES ('admin','Admin',1,0),('invitee','Invitee',1,0)")
            c.exec_driver_sql("INSERT INTO business_profiles (id,business_code,legal_name,display_name,business_type,verification_status,is_active) VALUES ('b1','B1','B1','B1','retail','verified',1)")
            c.exec_driver_sql("INSERT INTO business_memberships (id,business_id,user_id,membership_role,status) VALUES ('am','b1','admin','administrator','active')")
            c.exec_driver_sql("INSERT INTO business_role_permissions VALUES ('p1','administrator','business.member.manage')")
        with Session(engine) as db:
            admin=SimpleNamespace(id="admin")
            with pytest.raises(HTTPException) as owner_err:
                invite_member("b1",MembershipInvite(user_id="invitee",membership_role="owner"),user=admin,db=db)
            assert owner_err.value.status_code == 422
            with pytest.raises(HTTPException) as admin_err:
                invite_member("b1",MembershipInvite(user_id="invitee",membership_role="administrator"),user=admin,db=db)
            assert admin_err.value.status_code == 403
    finally:
        engine.dispose()


def test_only_platform_owner_can_verify_business_and_decision_is_audited():
    engine=db_fixture()
    try:
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO users VALUES ('owner','Owner',1,0),('admin','Admin',1,0)")
            c.exec_driver_sql("INSERT INTO roles VALUES ('ro','owner'),('ra','admin')")
            c.exec_driver_sql("INSERT INTO permissions VALUES ('pv','business.verification.manage')")
            c.exec_driver_sql("INSERT INTO role_permissions VALUES ('ro','pv'),('ra','pv')")
            c.exec_driver_sql("INSERT INTO user_roles VALUES ('owner','ro',NULL),('admin','ra',NULL)")
            c.exec_driver_sql("INSERT INTO business_profiles (id,business_code,legal_name,display_name,business_type,verification_status,is_active) VALUES ('b1','B1','B1','B1','retail','pending',1)")
            c.exec_driver_sql("INSERT INTO business_memberships (id,business_id,user_id,membership_role,status) VALUES ('om','b1','owner','owner','pending')")
        with Session(engine) as db:
            dep=require_permission("business.verification.manage")
            with pytest.raises(HTTPException) as err:
                dep(user=SimpleNamespace(id="admin"),db=db)
            assert err.value.status_code == 403
            owner=dep(user=SimpleNamespace(id="owner"),db=db)
            result=verify_business("b1",VerificationDecision(status="verified",notes="Documents checked",evidence_refs=["synthetic://evidence/1"]),owner=owner,db=db)
            assert result["verification_status"] == "verified"
            assert db.execute(text("SELECT verification_status,is_active FROM business_profiles WHERE id='b1'")).one() == ("verified",1)
            assert db.execute(text("SELECT status FROM business_memberships WHERE id='om'")).scalar_one() == "active"
            assert db.execute(text("SELECT actor_id,previous_status,new_status,notes FROM business_verification_events")).one() == ("owner","pending","verified","Documents checked")
            assert db.execute(text("SELECT event_type FROM business_membership_events WHERE membership_id='om'")).scalar_one() == "business.membership.activated_by_verification"
    finally:
        engine.dispose()


def test_owner_rejection_and_suspension_transitions_are_audited():
    engine=db_fixture()
    try:
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO users VALUES ('owner','Owner',1,0)")
            c.exec_driver_sql("INSERT INTO business_profiles (id,business_code,legal_name,display_name,business_type,verification_status,is_active) VALUES ('reject-b','RB','Reject PLC','Reject','retail','pending',1),('suspend-b','SB','Suspend PLC','Suspend','retail','verified',1)")
        with Session(engine) as db:
            owner=SimpleNamespace(id="owner")
            rejected=verify_business("reject-b",VerificationDecision(status="rejected",notes="Registration evidence insufficient",evidence_refs=["synthetic://evidence/reject"]),owner=owner,db=db)
            assert rejected["verification_status"] == "rejected"
            reject_state=db.execute(text("SELECT verification_status,is_active FROM business_profiles WHERE id='reject-b'")).one()
            assert reject_state == ("rejected",0)
            suspended=verify_business("suspend-b",VerificationDecision(status="suspended",notes="Verification temporarily suspended",evidence_refs=["synthetic://evidence/suspend"]),owner=owner,db=db)
            assert suspended["verification_status"] == "suspended"
            suspend_state=db.execute(text("SELECT verification_status,is_active,suspended_at IS NOT NULL FROM business_profiles WHERE id='suspend-b'")).one()
            assert suspend_state == ("suspended",0,1)
            audit=db.execute(text("SELECT business_id,actor_id,previous_status,new_status,notes FROM business_verification_events ORDER BY business_id")).all()
            assert tuple(audit[0]) == ("reject-b","owner","pending","rejected","Registration evidence insufficient")
            assert tuple(audit[1]) == ("suspend-b","owner","verified","suspended","Verification temporarily suspended")
    finally:
        engine.dispose()
