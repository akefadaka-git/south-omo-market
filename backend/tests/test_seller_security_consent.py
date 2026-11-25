from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.governance import require_seller_business_listing_access
from app.routers.inquiries import InquiryCreate, _inquiry_payload


def _seller_access_db(*, verified=True, active=True, membership="active", role="owner", user_active=True, suspended=False):
    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.exec_driver_sql("CREATE TABLE users (id TEXT, is_active BOOLEAN, is_suspended BOOLEAN)")
        c.exec_driver_sql("CREATE TABLE seller_profiles (id TEXT, user_id TEXT, business_id TEXT)")
        c.exec_driver_sql("CREATE TABLE business_profiles (id TEXT, is_active BOOLEAN, verification_status TEXT)")
        c.exec_driver_sql("CREATE TABLE business_memberships (business_id TEXT, user_id TEXT, status TEXT, expires_at DATETIME, membership_role TEXT)")
        c.exec_driver_sql("INSERT INTO users VALUES ('u1', ?, ?)", (user_active, suspended))
        c.exec_driver_sql("INSERT INTO seller_profiles VALUES ('s1','u1','b1')")
        c.exec_driver_sql("INSERT INTO business_profiles VALUES ('b1', ?, ?)", (active, "verified" if verified else "pending"))
        c.exec_driver_sql("INSERT INTO business_memberships VALUES ('b1','u1',?,NULL,?)", (membership, role))
    return engine


@pytest.mark.parametrize("kwargs", [
    {"verified": False},
    {"active": False},
    {"membership": "pending"},
    {"membership": "revoked"},
    {"role": "finance"},
    {"role": "viewer"},
    {"user_active": False},
    {"suspended": True},
])
def test_seller_listing_access_fails_closed(kwargs):
    engine = _seller_access_db(**kwargs)
    try:
        with Session(engine) as db, pytest.raises(HTTPException) as err:
            require_seller_business_listing_access(db, SimpleNamespace(id="u1"))
        assert err.value.status_code == 403
    finally:
        engine.dispose()


def test_verified_business_active_listing_member_is_authorized():
    engine = _seller_access_db()
    try:
        with Session(engine) as db:
            require_seller_business_listing_access(db, SimpleNamespace(id="u1"))
    finally:
        engine.dispose()


def test_inquiry_requires_explicit_contact_disclosure_choice():
    with pytest.raises(Exception):
        InquiryCreate(listing_id="listing-1", message="Please call me")


def test_inquiry_payload_never_discloses_contact_without_consent():
    inquiry = SimpleNamespace(
        id="i1", message="Interested", status="open", created_at=datetime.now(),
        read_at=None, closed_at=None, buyer_name="Marketplace customer",
        contact_value=None, buyer_user_id="buyer-1", contact_disclosure_consent=False,
    )
    listing = SimpleNamespace(id="l1", title="Tomatoes")
    payload = _inquiry_payload(inquiry, listing, include_buyer_contact=True)
    assert payload["contact_disclosure_consent"] is False
    assert "buyer_contact" not in payload
    assert "buyer_user_id" not in payload
    assert payload["buyer_name"] == "Marketplace customer"


def test_inquiry_payload_discloses_contact_only_after_consent():
    inquiry = SimpleNamespace(
        id="i1", message="Interested", status="open", created_at=datetime.now(),
        read_at=None, closed_at=None, buyer_name="Buyer",
        contact_value="+251900000000", buyer_user_id="buyer-1",
        contact_disclosure_consent=True,
    )
    listing = SimpleNamespace(id="l1", title="Tomatoes")
    payload = _inquiry_payload(inquiry, listing, include_buyer_contact=True)
    assert payload["buyer_contact"] == "+251900000000"
