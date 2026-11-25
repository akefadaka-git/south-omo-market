from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.image_storage import LocalImageStorage, get_image_storage
from app.core.rate_limit import limiter
from app.main import app
from app import models  # noqa: F401
from app.models import Category, Listing, Location, SellerProfile, User
from app.governance_models import BusinessMembership, BusinessProfile
from app.seeders.system_reference import seed_system_reference_data

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)
with TestingSession() as seed_db:
    seed_system_reference_data(seed_db)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def test_register_and_login_with_synthetic_account() -> None:
    created = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000001",
        "display_name": "Synthetic Seller",
        "password": "synthetic-password-123",
    })
    assert created.status_code == 201
    assert "password" not in created.json()
    login = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000001",
        "password": "synthetic-password-123",
    })
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_seller_can_manage_only_own_draft_and_submit_for_review() -> None:
    db = TestingSession()
    category_id = "00000000-0000-4000-8000-000000000001"
    if db.get(Category, category_id) is None:
        db.add(Category(
            id=category_id, slug="test-livestock", name_en="Test livestock", is_active=True
        ))
    koybe_id = "10000000-0000-4000-8000-000000000003"
    if db.get(Location, koybe_id) is None:
        db.add(Location(
            id=koybe_id,
            parent_id="10000000-0000-4000-8000-000000000002",
            code="ET-SO-MAALE-KOYBE",
            level="locality",
            name_en="Koybe",
            name_am="ቆይቤ",
            name_mdy=None,
            is_active=True,
        ))
    db.commit()
    db.close()

    registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000002",
        "display_name": "Lifecycle Seller",
        "password": "synthetic-password-456",
    })
    assert registration.status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000002",
        "password": "synthetic-password-456",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Synthetic Livestock Seller",
        "location_label": "Koybe",
    })
    assert profile.status_code == 201
    profile_read = client.get("/api/v1/sellers/me", headers=headers)
    assert profile_read.status_code == 200
    assert profile_read.json()["public_name"] == "Synthetic Livestock Seller"

    created = client.post("/api/v1/listings", headers=headers, json={
        "category_id": category_id,
        "title": "Synthetic cattle listing",
        "description": "Test-only listing",
        "price_minor": 125000,
        "location_label": "Koybe",
    })
    assert created.status_code == 201
    listing_id = created.json()["id"]
    my_listings = client.get("/api/v1/listings/my", headers=headers)
    assert my_listings.status_code == 200
    created_listing = next(row for row in my_listings.json() if row["id"] == listing_id)
    assert created_listing["location_id"] == "10000000-0000-4000-8000-000000000003"

    mine = client.get("/api/v1/listings/my", headers=headers)
    assert mine.status_code == 200
    assert any(item["id"] == listing_id and item["status"] == "draft" for item in mine.json())

    updated = client.patch(f"/api/v1/listings/{listing_id}", headers=headers, json={
        "title": "Updated synthetic cattle listing",
    })
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated synthetic cattle listing"

    submitted = client.post(f"/api/v1/listings/{listing_id}/submit", headers=headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_review"

    locked = client.patch(f"/api/v1/listings/{listing_id}", headers=headers, json={
        "title": "Attempted post-submission edit",
    })
    assert locked.status_code == 409

    public = client.get(f"/api/v1/listings/{listing_id}")
    assert public.status_code == 404

    other_registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000003",
        "display_name": "Other Synthetic Seller",
        "password": "synthetic-password-789",
    })
    assert other_registration.status_code == 201
    other_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000003",
        "password": "synthetic-password-789",
    }).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_profile = client.post("/api/v1/sellers/me", headers=other_headers, json={
        "public_name": "Other Seller",
        "location_label": "Jinka",
    })
    assert other_profile.status_code == 201
    assert client.get("/api/v1/listings/my", headers=other_headers).json() == []
    hidden = client.patch(f"/api/v1/listings/{listing_id}", headers=other_headers, json={
        "title": "Cross-seller modification",
    })
    assert hidden.status_code == 404


def test_only_admin_can_approve_pending_listing() -> None:
    seller_token = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000101",
        "display_name": "Synthetic Seller",
        "password": "synthetic-test-password-123",
    })
    assert seller_token.status_code == 201
    seller_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000101",
        "password": "synthetic-test-password-123",
    }).json()["access_token"]
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    profile = client.post("/api/v1/sellers/me", headers=seller_headers, json={
        "public_name": "Test Livestock Seller", "location_label": "Koybe",
    })
    assert profile.status_code == 201
    category_id = "00000000-0000-4000-8000-000000000001"
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="livestock", name_en="Livestock", is_active=True))
        db.commit()
    db.close()
    created = client.post("/api/v1/listings", headers=seller_headers, json={
        "category_id": category_id, "title": "Synthetic cattle for moderation",
        "description": "Synthetic moderation test", "price_minor": 100000,
        "location_label": "Koybe",
    })
    assert created.status_code == 201
    listing_id = created.json()["id"]
    assert client.post(f"/api/v1/listings/{listing_id}/submit", headers=seller_headers).status_code == 200
    assert client.get("/api/v1/admin/moderation/queue", headers=seller_headers).status_code == 403

    registered = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000102", "display_name": "Synthetic Admin",
        "password": "synthetic-test-password-123",
    })
    assert registered.status_code == 201
    db = TestingSession()
    from app.admin_cli import set_admin_role
    admin = set_admin_role(db, "+251900000102", grant=True, operator="synthetic-test-operator")
    assert admin.is_admin is True
    db.close()
    admin_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000102",
        "password": "synthetic-test-password-123",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    queue = client.get("/api/v1/admin/moderation/queue", headers=admin_headers)
    assert queue.status_code == 200
    assert any(item["id"] == listing_id for item in queue.json())
    decision = client.post(
        f"/api/v1/admin/moderation/{listing_id}/decision",
        headers=admin_headers,
        json={"decision": "approve", "note": "Synthetic test approval"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "published"
    assert client.get(f"/api/v1/listings/{listing_id}").status_code == 200

    from app.models import AuditEvent
    event = db.query(AuditEvent).filter_by(
        resource_type="listing", resource_id=listing_id,
        action="listing.moderation.approved",
    ).one()
    assert event.actor_id == admin.id
    assert event.event_metadata["new_status"] == "published"
    history = client.get(
        "/api/v1/admin/audit-events",
        headers=admin_headers,
        params={"resource_type": "listing", "resource_id": listing_id},
    )
    assert history.status_code == 200
    assert history.json()[0]["action"] == "listing.moderation.approved"
    assert client.get("/api/v1/admin/audit-events", headers=seller_headers).status_code == 403


def test_admin_provisioning_is_out_of_band_and_last_admin_is_protected() -> None:
    from app.admin_cli import set_admin_role

    registered = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000201",
        "display_name": "Provisioning Target",
        "password": "synthetic-test-password-201",
    })
    assert registered.status_code == 201
    db = TestingSession()
    target = db.query(models.User).filter_by(phone_number="+251900000201").one()
    # Isolate the last-admin invariant from accounts created by other tests.
    db.query(models.User).filter(models.User.is_admin.is_(True)).update(
        {models.User.is_admin: False}, synchronize_session=False
    )
    db.commit()
    assert target.is_admin is False
    assert client.post("/api/v1/admin/provision", json={"phone_number": target.phone_number}).status_code == 404

    try:
        set_admin_role(db, target.phone_number, grant=True, operator=" ")
        assert False, "Blank operator identifiers must be rejected"
    except ValueError as error:
        assert "Operator identifier is required" in str(error)
    provisioned = set_admin_role(db, target.phone_number, grant=True, operator="synthetic-test-operator")
    assert provisioned.is_admin is True
    from app.models import AuditEvent
    grant_event = db.query(AuditEvent).filter_by(
        resource_id=target.id, action="admin.access.granted"
    ).one()
    assert grant_event.actor_id is None
    assert grant_event.event_metadata["operator"] == "synthetic-test-operator"
    try:
        set_admin_role(db, target.phone_number, grant=False, operator="synthetic-test-operator")
        assert False, "The last active administrator must not be revocable"
    except ValueError as error:
        assert "last active administrator" in str(error)
    assert db.get(models.User, target.id).is_admin is True
    db.close()


def test_seller_inquiry_inbox_is_scoped_to_owned_listings() -> None:
    seller_registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000301",
        "display_name": "Inbox Seller",
        "password": "synthetic-test-password-301",
    })
    assert seller_registration.status_code == 201
    seller_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000301",
        "password": "synthetic-test-password-301",
    }).json()["access_token"]
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    profile = client.post("/api/v1/sellers/me", headers=seller_headers, json={
        "public_name": "Inbox Seller Shop", "location_label": "Koybe",
    })
    assert profile.status_code == 201

    category_id = "00000000-0000-4000-8000-000000000001"
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="livestock", name_en="Livestock", is_active=True))
        db.commit()
    db.close()
    listing = client.post("/api/v1/listings", headers=seller_headers, json={
        "category_id": category_id, "title": "Published synthetic goats",
        "description": "Inbox test listing", "price_minor": 45000,
        "location_label": "Koybe",
    })
    assert listing.status_code == 201
    listing_id = listing.json()["id"]
    db = TestingSession()
    db.get(models.Listing, listing_id).status = "published"
    db.commit()
    db.close()
    assert client.post("/api/v1/inquiries", headers=seller_headers, json={
        "listing_id": listing_id, "message": "Self inquiry must be blocked",
    }).status_code == 409

    buyer_registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000302",
        "display_name": "Inbox Buyer",
        "password": "synthetic-test-password-302",
    })
    assert buyer_registration.status_code == 201
    buyer_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000302",
        "password": "synthetic-test-password-302",
    }).json()["access_token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    created = client.post("/api/v1/inquiries", headers=buyer_headers, json={
        "listing_id": listing_id, "message": "Is this item available?",
    })
    assert created.status_code == 201
    inquiry_id = created.json()["id"]

    inbox = client.get("/api/v1/inquiries/inbox", headers=seller_headers)
    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    assert inbox.json()[0]["buyer_contact"] == "+251900000302"
    assert inbox.json()[0]["status"] == "open"

    mine = client.get("/api/v1/inquiries/mine", headers=buyer_headers)
    assert mine.status_code == 200
    assert mine.json()[0]["id"] == inquiry_id
    assert "buyer_contact" not in mine.json()[0]

    assert client.patch(
        f"/api/v1/inquiries/{inquiry_id}/status",
        headers=buyer_headers, json={"status": "closed"},
    ).status_code == 403
    changed = client.patch(
        f"/api/v1/inquiries/{inquiry_id}/status",
        headers=seller_headers, json={"status": "read"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "read"
    closed = client.patch(
        f"/api/v1/inquiries/{inquiry_id}/status",
        headers=seller_headers, json={"status": "closed"},
    )
    assert closed.status_code == 200
    filtered = client.get(
        "/api/v1/inquiries/inbox", headers=seller_headers, params={"status": "closed"}
    )
    assert filtered.status_code == 200
    assert filtered.json()[0]["id"] == inquiry_id

    outsider_registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000303",
        "display_name": "Inbox Outsider",
        "password": "synthetic-test-password-303",
    })
    assert outsider_registration.status_code == 201
    outsider_token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000303",
        "password": "synthetic-test-password-303",
    }).json()["access_token"]
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    assert client.get("/api/v1/inquiries/inbox", headers=outsider_headers).status_code == 403
    outsider_profile = client.post("/api/v1/sellers/me", headers=outsider_headers, json={
        "public_name": "Different Seller", "location_label": "Jinka",
    })
    assert outsider_profile.status_code == 201
    assert client.get("/api/v1/inquiries/inbox", headers=outsider_headers).json() == []
    assert client.patch(
        f"/api/v1/inquiries/{inquiry_id}/status",
        headers=outsider_headers, json={"status": "closed"},
    ).status_code == 404


def _register_seller(phone: str) -> tuple[str, str]:
    created = client.post("/api/v1/auth/register", json={
        "phone_number": phone,
        "display_name": "Synthetic Offline Seller",
        "password": "synthetic-offline-password-123",
    })
    assert created.status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "phone_number": phone,
        "password": "synthetic-offline-password-123",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Synthetic Offline Shop", "location_label": "Koybe",
    })
    assert profile.status_code == 201
    return created.json()["id"], token


def test_offline_listing_sync_is_idempotent_and_seller_scoped() -> None:
    category_id = "00000000-0000-4000-8000-000000000001"
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="offline-livestock", name_en="Offline livestock", is_active=True))
        db.commit()
    db.close()
    _user_id, token = _register_seller("+251900000401")
    headers = {"Authorization": f"Bearer {token}"}
    sync_id = str(uuid4())
    payload = {
        "client_sync_id": sync_id,
        "category_id": category_id,
        "title": "Offline synthetic goats",
        "description": "Queued without network",
        "price_minor": 35000,
        "location_label": "Koybe",
    }
    first = client.post("/api/v1/listings/sync", headers=headers, json=payload)
    assert first.status_code == 200
    assert first.json()["idempotent"] is False
    replay = client.post("/api/v1/listings/sync", headers=headers, json=payload)
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["idempotent"] is True

    changed = {**payload, "title": "Changed content with same idempotency key"}
    assert client.post("/api/v1/listings/sync", headers=headers, json=changed).status_code == 409

    _other_id, other_token = _register_seller("+251900000402")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.post("/api/v1/listings/sync", headers=other_headers, json=payload).status_code == 409


def test_listing_image_upload_validates_content_and_hides_private_images(tmp_path, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("IMAGE_STORAGE_DIR", str(tmp_path / "private-images"))
    get_settings.cache_clear()
    try:
        _user_id, token = _register_seller("+251900000411")
        headers = {"Authorization": f"Bearer {token}"}
        category_id = "00000000-0000-4000-8000-000000000001"
        db = TestingSession()
        if db.get(Category, category_id) is None:
            db.add(Category(id=category_id, slug="image-livestock", name_en="Image livestock", is_active=True))
            db.commit()
        db.close()
        listing = client.post("/api/v1/listings", headers=headers, json={
            "category_id": category_id, "title": "Image test listing",
            "description": "Synthetic image test", "price_minor": 50000,
            "location_label": "Jinka",
        })
        assert listing.status_code == 201
        listing_id = listing.json()["id"]

        image_buffer = BytesIO()
        Image.new("RGB", (24, 16), "green").save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()
        image_id = str(uuid4())
        uploaded = client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=headers,
            data={"client_image_id": image_id},
            files={"file": ("synthetic.png", image_bytes, "image/png")},
        )
        assert uploaded.status_code == 201
        image = uploaded.json()
        assert image["width"] == 24 and image["height"] == 16
        assert client.get(image["url"]).status_code == 404

        replay = client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=headers,
            data={"client_image_id": image_id},
            files={"file": ("synthetic.png", image_bytes, "image/png")},
        )
        assert replay.status_code == 201
        assert replay.json()["id"] == image["id"]

        invalid = client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=headers,
            data={"client_image_id": str(uuid4())},
            files={"file": ("not-an-image.png", b"not an image", "image/png")},
        )
        assert invalid.status_code == 415

        oversized = client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=headers,
            data={"client_image_id": str(uuid4())},
            files={"file": ("oversized.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
        )
        assert oversized.status_code == 413

        for _ in range(4):
            additional = client.post(
                f"/api/v1/listings/{listing_id}/images",
                headers=headers,
                data={"client_image_id": str(uuid4())},
                files={"file": ("synthetic.png", image_bytes, "image/png")},
            )
            assert additional.status_code == 201
        over_limit = client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=headers,
            data={"client_image_id": str(uuid4())},
            files={"file": ("synthetic.png", image_bytes, "image/png")},
        )
        assert over_limit.status_code == 409

        db = TestingSession()
        db.get(models.Listing, listing_id).status = "published"
        db.commit()
        db.close()
        served = client.get(image["url"])
        assert served.status_code == 200
        assert served.headers["content-type"] == "image/jpeg"
        assert served.content.startswith(bytes.fromhex("ffd8"))

        _other_id, other_token = _register_seller("+251900000412")
        other_headers = {"Authorization": f"Bearer {other_token}"}
        assert client.post(
            f"/api/v1/listings/{listing_id}/images",
            headers=other_headers,
            data={"client_image_id": str(uuid4())},
            files={"file": ("synthetic.png", image_bytes, "image/png")},
        ).status_code == 404
    finally:
        get_settings.cache_clear()


def test_login_endpoint_enforces_ip_rate_limit() -> None:
    limiter.reset()
    payload = {
        "phone_number": "+251900000099",
        "password": "synthetic-password-123",
    }
    for _ in range(20):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
    blocked = client.post("/api/v1/auth/login", json=payload)
    assert blocked.status_code == 429
    limiter.reset()



def test_localized_category_and_hierarchical_location_catalog() -> None:
    db = TestingSession()
    category_id = "00000000-0000-4000-8000-000000000006"
    location_id = "10000000-0000-4000-8000-000000000003"
    parent_id = "10000000-0000-4000-8000-000000000002"
    if db.get(Category, category_id) is None:
        db.add(Category(
            id=category_id, slug="test-rentals", name_en="Property and rentals",
            name_am="ንብረት እና ኪራይ", is_active=True,
        ))
    if db.get(Location, parent_id) is None:
        db.add(Location(
            id=parent_id, code="TEST-MAALE", level="woreda",
            name_en="Maale", name_am="ማሌ", name_mdy=None, is_active=True,
        ))
    if db.get(Location, location_id) is None:
        db.add(Location(
            id=location_id, parent_id=parent_id, code="TEST-KOYBE", level="locality",
            name_en="Koybe", name_am="ቆይቤ", name_mdy=None, is_active=True,
        ))
    db.commit()
    db.close()

    categories = client.get("/api/v1/categories?lang=am")
    assert categories.status_code == 200
    translated = next(row for row in categories.json() if row["id"] == category_id)
    assert translated["name"] == "ንብረት እና ኪራይ"
    assert translated["name_en"] == "Property and rentals"

    locations = client.get(f"/api/v1/locations?parent_id={parent_id}&lang=am")
    assert locations.status_code == 200
    assert locations.json() == [{
        "id": location_id,
        "parent_id": parent_id,
        "code": "ET-SO-MAALE-KOYBE",
        "level": "locality",
        "name": "ቆይቤ",
        "name_en": "Koybe",
        "name_am": "ቆይቤ",
        "name_mdy": None,
    }]


def test_public_listing_location_filter_uses_normalized_location_id() -> None:
    suffix = uuid4().hex
    user_id = str(uuid4())
    seller_id = str(uuid4())
    category_id = str(uuid4())
    location_id = str(uuid4())
    listing_id = str(uuid4())
    db = TestingSession()
    db.add(User(
        id=user_id,
        phone_number=f"+2519{suffix[:8]}",
        display_name="Synthetic location-filter seller",
        password_hash="not-a-real-login-hash",
        is_active=True,
        is_admin=False,
        is_suspended=False,
    ))
    db.add(SellerProfile(
        id=seller_id,
        user_id=user_id,
        public_name="Synthetic location-filter seller",
        location_label="Koybe",
    ))
    db.add(Category(
        id=category_id,
        slug=f"location-filter-{suffix}",
        name_en="Location filter test",
        is_active=True,
    ))
    db.add(Location(
        id=location_id,
        code=f"location-filter-{suffix}",
        level="kebele",
        name_en="Koybe",
    ))
    db.add(Listing(
        id=listing_id,
        seller_id=seller_id,
        category_id=category_id,
        title="Synthetic Koybe listing",
        description="Test-only listing",
        price_minor=10000,
        currency="ETB",
        location_label="Koybe",
        location_id=location_id,
        status="published",
    ))
    db.commit()
    db.close()

    matching = client.get(f"/api/v1/listings?location_id={location_id}")
    nonmatching = client.get(f"/api/v1/listings?location_id={uuid4()}")
    assert matching.status_code == 200
    assert listing_id in {row["id"] for row in matching.json()}
    assert nonmatching.status_code == 200
    assert all(row["id"] != listing_id for row in nonmatching.json())


def test_public_discovery_searches_descriptions_and_sorts_prices() -> None:
    from app.models import SellerProfile, User

    suffix = uuid4().hex[:8]
    category_id = "00000000-0000-4000-8000-000000000001"
    seller_id = str(uuid4())
    user_id = str(uuid4())
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(
            id=category_id, slug=f"discovery-{suffix}", name_en="Discovery", is_active=True
        ))
    db.add(User(
        id=user_id, phone_number=f"+2519{suffix[:8]}", display_name="Synthetic Discovery",
        password_hash="not-a-real-login-hash", is_active=True, is_admin=False,
    ))
    db.add(SellerProfile(
        id=seller_id, user_id=user_id, public_name="Synthetic Discovery Seller",
        location_label="Koybe",
    ))
    db.add_all([
        Listing(
            id=str(uuid4()), seller_id=seller_id, category_id=category_id,
            title=f"Discovery low {suffix}", description="seasonal mango produce",
            price_minor=2500, currency="ETB", location_label="Koybe",
            status="published",
        ),
        Listing(
            id=str(uuid4()), seller_id=seller_id, category_id=category_id,
            title=f"Discovery high {suffix}", description="fresh cattle feed",
            price_minor=7500, currency="ETB", location_label="Jinka",
            status="published",
        ),
    ])
    db.commit()
    db.close()

    searched = client.get("/api/v1/listings", params={"q": "mango", "limit": 100})
    assert searched.status_code == 200
    assert len(searched.json()) == 1
    assert "mango" in searched.json()[0]["description"]

    ascending = client.get("/api/v1/listings", params={"q": suffix, "sort": "price_asc"})
    assert ascending.status_code == 200
    assert [row["price_minor"] for row in ascending.json()] == [2500, 7500]

    descending = client.get("/api/v1/listings", params={"q": suffix, "sort": "price_desc"})
    assert descending.status_code == 200
    assert [row["price_minor"] for row in descending.json()] == [7500, 2500]

    invalid_sort = client.get("/api/v1/listings", params={"sort": "random"})
    assert invalid_sort.status_code == 422


def test_category_hierarchy_and_category_specific_listing_attributes() -> None:
    from app.models import SellerProfile, User

    root_id = "00000000-0000-4000-8000-000000000001"
    child_id = "40000000-0000-4000-8000-000000000001"
    db = TestingSession()
    root = db.get(Category, root_id)
    if root is None:
        root = Category(id=root_id, slug="hierarchy-root", name_en="Livestock", is_active=True)
        db.add(root)
    child = db.get(Category, child_id)
    if child is None:
        db.add(Category(
            id=child_id, slug="hierarchy-cattle", name_en="Cattle",
            parent_id=root_id, is_active=True,
            attributes_schema=[
                {"key": "breed", "type": "text", "required": True, "max_length": 80},
                {"key": "age_months", "type": "number", "required": True, "min": 0, "max": 600},
                {"key": "sex", "type": "choice", "required": True, "options": ["female", "male"]},
            ],
        ))
    db.commit()
    db.close()

    roots = client.get("/api/v1/categories", params={"roots_only": "true"})
    assert roots.status_code == 200
    root_row = next(row for row in roots.json() if row["id"] == root_id)
    assert root_row["is_leaf"] is False

    children = client.get("/api/v1/categories", params={"parent_id": root_id})
    assert children.status_code == 200
    child_row = next(row for row in children.json() if row["id"] == child_id)
    assert child_row["parent_id"] == root_id
    assert child_row["is_leaf"] is True
    assert {field["key"] for field in child_row["attributes_schema"]} == {"breed", "age_months", "sex"}

    _user_id, token = _register_seller("+251900000499")
    headers = {"Authorization": f"Bearer {token}"}
    root_listing = client.post("/api/v1/listings", headers=headers, json={
        "category_id": root_id, "title": "Root category listing",
        "price_minor": 1000, "location_label": "Koybe",
    })
    assert root_listing.status_code == 422

    payload = {
        "category_id": child_id, "title": "Synthetic cattle listing",
        "description": "Test only", "price_minor": 250000,
        "location_label": "Koybe",
        "attributes": {"breed": "Local", "age_months": 36, "sex": "female"},
    }
    created = client.post("/api/v1/listings", headers=headers, json=payload)
    assert created.status_code == 201
    mine = client.get("/api/v1/listings/my", headers=headers)
    assert mine.status_code == 200
    saved = next(row for row in mine.json() if row["id"] == created.json()["id"])
    assert saved["attributes"] == payload["attributes"]

    invalid = {**payload, "attributes": {"breed": "Local", "age_months": 900, "sex": "unknown"}}
    rejected = client.post("/api/v1/listings", headers=headers, json=invalid)
    assert rejected.status_code == 422



def test_expanded_category_catalogue_and_listing_attribute_contract() -> None:
    root_id = "50000000-0000-4000-8000-000000000001"
    leaf_id = "50000000-0000-4000-8000-000000000002"
    schema = [
        {"key": "produce", "type": "text", "required": True, "max_length": 80},
        {"key": "quantity", "type": "number", "required": True, "min": 1, "max": 10000},
        {"key": "unit", "type": "choice", "required": True, "options": ["kg", "quintal"]},
        {"key": "organic", "type": "boolean", "required": False},
    ]
    db = TestingSession()
    if db.get(Category, root_id) is None:
        db.add(Category(
            id=root_id, slug="test-expanded-root", name_en="Test expanded catalogue",
            is_active=True, attributes_schema=[],
        ))
    if db.get(Category, leaf_id) is None:
        db.add(Category(
            id=leaf_id, slug="test-expanded-produce", name_en="Test produce",
            parent_id=root_id, is_active=True, attributes_schema=schema,
        ))
    db.commit()
    db.close()

    catalogue = client.get("/api/v1/categories", params={"parent_id": root_id})
    assert catalogue.status_code == 200
    assert len(catalogue.json()) == 1
    assert catalogue.json()[0]["slug"] == "test-expanded-produce"
    assert catalogue.json()[0]["is_leaf"] is True
    assert catalogue.json()[0]["attributes_schema"] == schema

    registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000601",
        "display_name": "Catalogue Integration Seller",
        "password": "synthetic-catalogue-password-601",
    })
    assert registration.status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000601",
        "password": "synthetic-catalogue-password-601",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Catalogue Test Seller", "location_label": "Koybe",
    })
    assert profile.status_code == 201

    base_payload = {
        "category_id": leaf_id,
        "title": "Synthetic produce listing",
        "description": "Catalogue contract test",
        "price_minor": 25000,
        "location_label": "Koybe",
    }
    missing = client.post("/api/v1/listings", headers=headers, json=base_payload)
    assert missing.status_code == 422
    invalid_choice = client.post("/api/v1/listings", headers=headers, json={
        **base_payload,
        "attributes": {"produce": "Maize", "quantity": 10, "unit": "truck"},
    })
    assert invalid_choice.status_code == 422
    invalid_range = client.post("/api/v1/listings", headers=headers, json={
        **base_payload,
        "attributes": {"produce": "Maize", "quantity": 0, "unit": "kg"},
    })
    assert invalid_range.status_code == 422
    unknown_field = client.post("/api/v1/listings", headers=headers, json={
        **base_payload,
        "attributes": {
            "produce": "Maize", "quantity": 10, "unit": "kg", "unapproved": "value",
        },
    })
    assert unknown_field.status_code == 422

    created = client.post("/api/v1/listings", headers=headers, json={
        **base_payload,
        "attributes": {"produce": "Maize", "quantity": 10, "unit": "kg", "organic": False},
    })
    assert created.status_code == 201
    listing_id = created.json()["id"]
    saved = client.get("/api/v1/listings/my", headers=headers)
    listing = next(item for item in saved.json() if item["id"] == listing_id)
    assert listing["attributes"] == {
        "produce": "Maize", "quantity": 10, "unit": "kg", "organic": False,
    }

    rejected_update = client.patch(f"/api/v1/listings/{listing_id}", headers=headers, json={
        "attributes": {"produce": "Maize", "quantity": 10001, "unit": "kg"},
    })
    assert rejected_update.status_code == 422
    accepted_update = client.patch(f"/api/v1/listings/{listing_id}", headers=headers, json={
        "attributes": {"produce": "Sorghum", "quantity": 25, "unit": "quintal"},
    })
    assert accepted_update.status_code == 200
    assert accepted_update.json()["attributes"]["produce"] == "Sorghum"

    parent_listing = client.post("/api/v1/listings", headers=headers, json={
        **base_payload, "category_id": root_id,
        "attributes": {"produce": "Maize", "quantity": 10, "unit": "kg"},
    })
    assert parent_listing.status_code == 422

    sync_payload = {
        **base_payload,
        "attributes": {"produce": "Teff", "quantity": 5, "unit": "kg"},
        "client_sync_id": str(uuid4()),
    }
    rejected_sync = client.post("/api/v1/listings/sync", headers=headers, json={
        **sync_payload, "attributes": {"produce": "Teff", "quantity": -1, "unit": "kg"},
    })
    assert rejected_sync.status_code == 422
    accepted_sync = client.post("/api/v1/listings/sync", headers=headers, json=sync_payload)
    assert accepted_sync.status_code == 200
    synced = client.get("/api/v1/listings/my", headers=headers)
    synced_listing = next(
        item for item in synced.json() if item["id"] == accepted_sync.json()["id"]
    )
    assert synced_listing["attributes"]["produce"] == "Teff"


def test_category_attribute_validator_rejects_malformed_schema_and_non_finite_values() -> None:
    from fastapi import HTTPException
    from app.routers.listings import _validated_attributes

    category = Category(
        id="test-schema", slug="test-schema", name_en="Test schema", is_active=True,
        attributes_schema=[
            {"key": "amount", "type": "number", "required": True, "min": 0, "max": 10},
        ],
    )
    with pytest.raises(HTTPException) as non_finite:
        _validated_attributes(category, {"amount": float("nan")})
    assert non_finite.value.status_code == 422

    category.attributes_schema = [
        {"key": "amount", "type": "unsupported", "required": True},
    ]
    with pytest.raises(HTTPException) as malformed:
        _validated_attributes(category, {"amount": 1})
    assert malformed.value.status_code == 500


def test_listing_and_seller_reports_evidence_review_blocks_and_audit() -> None:
    from app.admin_cli import set_admin_role
    from app.models import AuditEvent, Report, SellerProfile, User

    category_id = "70000000-0000-4000-8000-000000000001"
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="report-test-category", name_en="Report test category", is_active=True))
        db.commit()
    db.close()

    seller_phone = "+251900000701"
    assert client.post("/api/v1/auth/register", json={
        "phone_number": seller_phone, "display_name": "Report Test Seller",
        "password": "synthetic-report-seller-701",
    }).status_code == 201
    seller_token = client.post("/api/v1/auth/login", json={
        "phone_number": seller_phone, "password": "synthetic-report-seller-701",
    }).json()["access_token"]
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    profile = client.post("/api/v1/sellers/me", headers=seller_headers, json={
        "public_name": "Report Test Shop", "location_label": "Koybe",
    })
    assert profile.status_code == 201
    seller_id = profile.json()["id"]
    listing = client.post("/api/v1/listings", headers=seller_headers, json={
        "category_id": category_id, "title": "Reported synthetic item",
        "description": "Test-only report target", "price_minor": 50000,
        "location_label": "Koybe",
    })
    assert listing.status_code == 201
    listing_id = listing.json()["id"]
    db = TestingSession()
    db.get(Listing, listing_id).status = "published"
    db.commit()
    db.close()

    reporter_phone = "+251900000702"
    assert client.post("/api/v1/auth/register", json={
        "phone_number": reporter_phone, "display_name": "Report Author",
        "password": "synthetic-report-author-702",
    }).status_code == 201
    reporter_token = client.post("/api/v1/auth/login", json={
        "phone_number": reporter_phone, "password": "synthetic-report-author-702",
    }).json()["access_token"]
    reporter_headers = {"Authorization": f"Bearer {reporter_token}"}

    listing_report = client.post("/api/v1/reports", headers=reporter_headers, json={
        "listing_id": listing_id,
        "reason": "misleading_information",
        "description": "The item description materially conflicts with the advertised item.",
        "evidence": [{"summary": "Photograph and seller message show a different item.", "reference": "conversation reference 01"}],
    })
    assert listing_report.status_code == 201
    listing_report_id = listing_report.json()["id"]
    own_listing = client.post("/api/v1/reports", headers=seller_headers, json={
        "listing_id": listing_id, "reason": "other",
        "description": "This is an attempted self report.",
    })
    assert own_listing.status_code == 422
    my_reports = client.get("/api/v1/reports/my", headers=reporter_headers)
    assert my_reports.status_code == 200
    assert my_reports.json()[0]["id"] == listing_report_id
    assert my_reports.json()[0]["status"] == "pending"

    admin_phone = "+251900000703"
    assert client.post("/api/v1/auth/register", json={
        "phone_number": admin_phone, "display_name": "Report Moderator",
        "password": "synthetic-report-admin-703",
    }).status_code == 201
    db = TestingSession()
    admin = set_admin_role(db, admin_phone, grant=True, operator="synthetic-report-test")
    db.close()
    admin_token = client.post("/api/v1/auth/login", json={
        "phone_number": admin_phone, "password": "synthetic-report-admin-703",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    queue = client.get("/api/v1/admin/reports", headers=admin_headers)
    assert queue.status_code == 200
    queued = next(row for row in queue.json() if row["id"] == listing_report_id)
    assert queued["evidence"][0]["reference"] == "conversation reference 01"
    assert queued["target"]["type"] == "listing"

    investigated = client.post(f"/api/v1/admin/reports/{listing_report_id}/decision",
        headers=admin_headers, json={"decision": "investigate", "note": "Evidence review started"})
    assert investigated.status_code == 200
    assert investigated.json()["status"] == "in_review"
    blocked_listing = client.post(f"/api/v1/admin/reports/{listing_report_id}/decision",
        headers=admin_headers, json={"decision": "block_listing", "note": "Confirmed misleading listing"})
    assert blocked_listing.status_code == 200
    assert blocked_listing.json()["status"] == "in_review"
    assert client.get(f"/api/v1/listings/{listing_id}").status_code == 404
    premature_dismiss = client.post(f"/api/v1/admin/reports/{listing_report_id}/decision",
        headers=admin_headers, json={"decision": "dismiss", "note": "Must restore before dismissal"})
    assert premature_dismiss.status_code == 409
    restored_listing = client.post(f"/api/v1/admin/reports/{listing_report_id}/decision",
        headers=admin_headers, json={"decision": "restore_listing", "note": "Listing evidence did not support removal"})
    assert restored_listing.status_code == 200
    assert restored_listing.json()["status"] == "in_review"
    assert client.get(f"/api/v1/listings/{listing_id}").status_code == 200
    resolved_listing_report = client.post(f"/api/v1/admin/reports/{listing_report_id}/decision",
        headers=admin_headers, json={"decision": "resolve", "note": "Reviewed and restored"})
    assert resolved_listing_report.status_code == 200
    assert resolved_listing_report.json()["status"] == "resolved"

    visible_listing = client.post("/api/v1/listings", headers=seller_headers, json={
        "category_id": category_id, "title": "Seller suspension visibility check",
        "description": "Synthetic second listing", "price_minor": 70000,
        "location_label": "Koybe",
    })
    assert visible_listing.status_code == 201
    visible_listing_id = visible_listing.json()["id"]
    db = TestingSession()
    db.get(Listing, visible_listing_id).status = "published"
    db.commit()
    db.close()

    seller_report = client.post("/api/v1/reports", headers=reporter_headers, json={
        "seller_id": seller_id, "reason": "impersonation",
        "description": "Seller profile appears to impersonate another local business.",
        "evidence": [{"summary": "Name and contact details supplied for moderator review."}],
    })
    assert seller_report.status_code == 201
    seller_report_id = seller_report.json()["id"]
    blocked_seller = client.post(f"/api/v1/admin/reports/{seller_report_id}/decision",
        headers=admin_headers, json={"decision": "block_seller", "note": "Account suspended pending verified review"})
    assert blocked_seller.status_code == 200
    assert client.post("/api/v1/auth/login", json={
        "phone_number": seller_phone, "password": "synthetic-report-seller-701",
    }).status_code == 401
    assert client.get("/api/v1/sellers/me", headers=seller_headers).status_code == 401
    suspended_report_close = client.post(f"/api/v1/admin/reports/{seller_report_id}/decision",
        headers=admin_headers, json={"decision": "resolve", "note": "Cannot close while suspended"})
    assert suspended_report_close.status_code == 409
    assert client.get(f"/api/v1/listings/{visible_listing_id}").status_code == 404
    assert visible_listing_id not in {
        row["id"] for row in client.get("/api/v1/listings").json()
    }

    reinstated = client.post(f"/api/v1/admin/reports/{seller_report_id}/decision",
        headers=admin_headers, json={"decision": "unblock_seller", "note": "Review cleared"})
    assert reinstated.status_code == 200
    duplicate_reinstatement = client.post(f"/api/v1/admin/reports/{seller_report_id}/decision",
        headers=admin_headers, json={"decision": "unblock_seller", "note": "Duplicate action must fail"})
    assert duplicate_reinstatement.status_code == 409
    resolved_seller_report = client.post(f"/api/v1/admin/reports/{seller_report_id}/decision",
        headers=admin_headers, json={"decision": "resolve", "note": "Seller reinstated after review"})
    assert resolved_seller_report.status_code == 200
    assert resolved_seller_report.json()["status"] == "resolved"
    assert client.post("/api/v1/auth/login", json={
        "phone_number": seller_phone, "password": "synthetic-report-seller-701",
    }).status_code == 200
    assert client.get("/api/v1/sellers/me", headers=seller_headers).status_code == 401
    assert client.get(f"/api/v1/listings/{visible_listing_id}").status_code == 200
    assert visible_listing_id in {
        row["id"] for row in client.get("/api/v1/listings").json()
    }

    db = TestingSession()
    assert db.get(User, admin.id).is_admin is True
    assert db.get(Report, seller_report_id).status == "resolved"
    actions = {
        row.action for row in db.query(AuditEvent).filter(
            AuditEvent.resource_id.in_([listing_report_id, seller_report_id])
        ).all()
    }
    assert "report.created" in actions
    assert "report.investigate" in actions
    assert "report.block_listing" in actions
    assert "report.restore_listing" in actions
    assert "report.block_seller" in actions
    assert "report.unblock_seller" in actions
    db.close()
    assert client.get("/api/v1/admin/reports", headers=reporter_headers).status_code == 403


def test_maale_market_directory_schedule_admin_and_public_calendar() -> None:
    from app.admin_cli import set_admin_role
    from app.models import AuditEvent, Market, MarketScheduleDay

    admin_phone = "+251900000811"
    registered = client.post("/api/v1/auth/register", json={
        "phone_number": admin_phone,
        "display_name": "Synthetic Market Admin",
        "password": "synthetic-market-admin-811",
    })
    assert registered.status_code == 201
    db = TestingSession()
    set_admin_role(db, admin_phone, grant=True, operator="synthetic-market-test")
    db.close()
    token = client.post("/api/v1/auth/login", json={
        "phone_number": admin_phone, "password": "synthetic-market-admin-811",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}

    buyer_phone = "+251900000812"
    assert client.post("/api/v1/auth/register", json={
        "phone_number": buyer_phone, "display_name": "Synthetic Buyer",
        "password": "synthetic-market-buyer-812",
    }).status_code == 201
    buyer_token = client.post("/api/v1/auth/login", json={
        "phone_number": buyer_phone, "password": "synthetic-market-buyer-812",
    }).json()["access_token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    assert client.get("/api/v1/admin/markets", headers=buyer_headers).status_code == 403

    owner_schedule = [
        ("MAALE-BENETA", "Beneta", [3]),
        ("MAALE-ASHEKER", "Asheker", [1]),
        ("MAALE-BOSHKORO", "Boshkoro", [5]),
        ("MAALE-BALA", "Bala", [1]),
        ("MAALE-KOYBE", "Koybe", [0]),
        ("MAALE-BOBO", "Bobo", [2]),
        ("MAALE-AJO", "Ajo", [5]),
        ("MAALE-GENTO", "Gento", [5]),
    ]
    created = {}
    for code, name, days in owner_schedule:
        response = client.post("/api/v1/admin/markets", headers=admin_headers, json={
            "code": code, "name": name, "location_id": None,
        })
        assert response.status_code == 201, response.text
        created[name] = response.json()["id"]
        scheduled = client.put(
            f"/api/v1/admin/markets/{created[name]}/schedule",
            headers=admin_headers, json={"days": days},
        )
        assert scheduled.status_code == 200
        assert scheduled.json()["schedule_days"] == days

    assert client.post("/api/v1/admin/markets", headers=buyer_headers, json={
        "code": "UNAUTHORIZED", "name": "Unauthorized market",
    }).status_code == 403
    duplicate_day = client.put(
        f"/api/v1/admin/markets/{created['Koybe']}/schedule",
        headers=admin_headers, json={"days": [0, 0]},
    )
    assert duplicate_day.status_code == 422
    invalid_day = client.put(
        f"/api/v1/admin/markets/{created['Koybe']}/schedule",
        headers=admin_headers, json={"days": [7]},
    )
    assert invalid_day.status_code == 422
    invalid_location = client.post("/api/v1/admin/markets", headers=admin_headers, json={
        "code": "INVALID-LOCATION", "name": "Synthetic market",
        "location_id": "missing-location",
    })
    assert invalid_location.status_code == 422

    weekly = client.get("/api/v1/markets/schedule")
    assert weekly.status_code == 200
    by_day = {
        day["weekday"]: [market["name"] for market in day["markets"]]
        for day in weekly.json()["days"]
    }
    assert by_day == {
        0: ["Koybe"], 1: ["Asheker", "Bala"], 2: ["Bobo"],
        3: ["Beneta"], 4: [], 5: ["Ajo", "Boshkoro", "Gento"], 6: [],
    }
    assert client.get("/api/v1/markets/by-day/5").status_code == 200
    assert {row["name"] for row in client.get("/api/v1/markets").json()} == {
        name for _code, name, _days in owner_schedule
    }
    assert client.get("/api/v1/markets/by-day/7").status_code == 422
    assert client.get("/api/v1/markets").json()[0]["location_id"] is None

    disabled = client.patch(
        f"/api/v1/admin/markets/{created['Ajo']}/status",
        headers=admin_headers, json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert "Ajo" not in {
        row["name"] for row in client.get("/api/v1/markets/by-day/5").json()
    }
    reenabled = client.patch(
        f"/api/v1/admin/markets/{created['Ajo']}/status",
        headers=admin_headers, json={"is_active": True},
    )
    assert reenabled.status_code == 200

    edited = client.patch(
        f"/api/v1/admin/markets/{created['Beneta']}",
        headers=admin_headers, json={"name": "Beneta Market", "location_id": None},
    )
    assert edited.status_code == 200
    assert edited.json()["name"] == "Beneta Market"
    blank_name = client.patch(
        f"/api/v1/admin/markets/{created['Beneta']}",
        headers=admin_headers, json={"name": "   "},
    )
    assert blank_name.status_code == 422

    db = TestingSession()
    assert db.query(Market).count() == 8
    assert db.query(MarketScheduleDay).count() == 8
    actions = {
        event.action for event in db.query(AuditEvent).filter(
            AuditEvent.resource_type == "market"
        ).all()
    }
    assert {"market.created", "market.updated", "market.schedule.updated", "market.status.updated"} <= actions
    db.close()


def test_market_search_effective_schedule_and_admin_audit() -> None:
    phone = "+251900000888"
    registered = client.post("/api/v1/auth/register", json={
        "phone_number": phone,
        "display_name": "Synthetic Market Admin",
        "password": "synthetic-market-password-123",
    })
    assert registered.status_code == 201
    db = TestingSession()
    from app.admin_cli import set_admin_role
    admin = set_admin_role(db, phone, grant=True, operator="synthetic-market-test")
    assert admin.is_admin is True
    db.close()
    token = client.post("/api/v1/auth/login", json={
        "phone_number": phone,
        "password": "synthetic-market-password-123",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/api/v1/admin/markets", headers=headers, json={
        "code": "SYNTHETIC-MARKET",
        "name": "Synthetic Test Market",
        "description": "Synthetic searchable description",
    })
    assert created.status_code == 201
    market_id = created.json()["id"]
    assert created.json()["description"] == "Synthetic searchable description"

    future_schedule = client.put(f"/api/v1/admin/markets/{market_id}/schedule", headers=headers, json={
        "days": [1], "effective_from": "2099-01-01", "effective_until": "2099-12-31",
    })
    assert future_schedule.status_code == 200
    assert future_schedule.json()["schedule_days"] == [1]
    assert future_schedule.json()["schedule_entries"][0]["effective_from"] == "2099-01-01"

    invalid_range = client.put(f"/api/v1/admin/markets/{market_id}/schedule", headers=headers, json={
        "days": [1], "effective_from": "2099-12-31", "effective_until": "2099-01-01",
    })
    assert invalid_range.status_code == 422

    visible = client.get("/api/v1/markets", params={"q": "searchable", "weekday": 1})
    assert visible.status_code == 200
    assert visible.json() == []

    active_schedule = client.put(f"/api/v1/admin/markets/{market_id}/schedule", headers=headers, json={
        "days": [1],
    })
    assert active_schedule.status_code == 200
    visible = client.get("/api/v1/markets", params={"q": "searchable", "weekday": 1})
    assert visible.status_code == 200
    assert [row["id"] for row in visible.json()] == [market_id]

    history = client.get("/api/v1/admin/markets/audit", headers=headers)
    assert history.status_code == 200
    assert any(event["action"] == "market.created" and event["resource_id"] == market_id for event in history.json())
    assert any(event["action"] == "market.schedule.updated" and event["resource_id"] == market_id for event in history.json())


def test_seller_role_and_policy_are_enforced_for_every_listing_write_path() -> None:
    category_id = str(uuid4())
    db = TestingSession()
    db.add(Category(
        id=category_id, slug=f"policy-test-{category_id[:8]}",
        name_en="Policy test category", is_active=True,
    ))
    db.commit()
    db.close()

    phone = "+251900009991"
    assert client.post("/api/v1/auth/register", json={
        "phone_number": phone, "display_name": "Policy Seller",
        "password": "synthetic-policy-seller-991",
    }).status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "phone_number": phone, "password": "synthetic-policy-seller-991",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Public account registration grants no marketplace role. A seller profile
    # is the explicit eligibility event that receives only the merchant role.
    db = TestingSession()
    user = db.query(User).filter(User.phone_number == phone).one()
    assert db.execute(text("""
        SELECT COUNT(*) FROM user_roles WHERE user_id=:uid
    """), {"uid": user.id}).scalar_one() == 0
    db.close()

    profile = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Policy Test Seller", "location_label": "Koybe",
    })
    assert profile.status_code == 201
    db = TestingSession()
    user = db.query(User).filter(User.phone_number == phone).one()
    assert db.execute(text("""
        SELECT r.code FROM user_roles ur JOIN roles r ON r.id=ur.role_id
        WHERE ur.user_id=:uid
    """), {"uid": user.id}).scalars().all() == ["merchant"]
    db.close()

    def deny(action: str) -> None:
        with TestingSession() as session:
            pack_id = session.execute(text("""
                SELECT id FROM policy_packs WHERE code='south-omo-default-deny'
            """)).scalar_one()
            session.execute(text("""
                INSERT INTO policy_rules
                    (id,policy_pack_id,rule_code,effect,subject,action,resource,conditions)
                VALUES (:id,:pack,'test-deny-' || :action,'deny','role:merchant',:action,'listings','{}')
            """), {"id": str(uuid4()), "pack": pack_id, "action": action})
            session.commit()

    base_payload = {
        "category_id": category_id, "title": "Policy controlled item",
        "description": "Synthetic policy regression", "price_minor": 1000,
        "location_label": "Koybe",
    }
    created = client.post("/api/v1/listings", headers=headers, json=base_payload)
    assert created.status_code == 201
    listing_id = created.json()["id"]

    deny("marketplace.listing.create")
    denied_create = client.post("/api/v1/listings", headers=headers, json={
        **base_payload, "title": "Denied create operation",
    })
    assert denied_create.status_code == 403

    deny("marketplace.listing.update")
    denied_update = client.patch(f"/api/v1/listings/{listing_id}", headers=headers, json={
        "title": "Denied update operation",
    })
    assert denied_update.status_code == 403

    deny("marketplace.listing.submit")
    denied_submit = client.post(f"/api/v1/listings/{listing_id}/submit", headers=headers)
    assert denied_submit.status_code == 403

    sync_payload = {
        **base_payload, "title": "Offline policy draft",
        "client_sync_id": str(uuid4()),
    }
    synced = client.post("/api/v1/listings/sync", headers=headers, json=sync_payload)
    assert synced.status_code == 200
    deny("marketplace.listing.sync")
    denied_sync = client.post("/api/v1/listings/sync", headers=headers, json={
        **base_payload, "title": "New offline policy draft",
        "client_sync_id": str(uuid4()),
    })
    assert denied_sync.status_code == 403

    # Replaying an already-synced payload is also subject to current policy.
    denied_replay = client.post("/api/v1/listings/sync", headers=headers, json=sync_payload)
    assert denied_replay.status_code == 403



def test_customer_registration_persists_profile_and_supports_private_read_update() -> None:
    location_id = "10000000-0000-4000-8000-000000000003"
    registration = client.post("/api/v1/auth/register", json={
        "phone_number": "+251 900-000-801",
        "display_name": "Synthetic Customer",
        "password": "synthetic-password-801",
        "preferred_location_id": location_id,
        "preferred_language": "am",
        "email": "  CUSTOMER@example.test ",
    })
    assert registration.status_code == 201
    assert registration.json()["phone_number"] == "+251900000801"
    assert "password_hash" not in registration.json()

    db = TestingSession()
    account = db.query(User).filter_by(phone_number="+251900000801").one()
    profile = db.query(models.CustomerProfile).filter_by(user_id=account.id).one()
    assert profile.preferred_location_id == location_id
    assert profile.preferred_language == "am"
    assert profile.email == "customer@example.test"
    db.close()

    token = client.post("/api/v1/auth/login", json={
        "phone_number": "+251900000801",
        "password": "synthetic-password-801",
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    read = client.get("/api/v1/customers/me", headers=headers)
    assert read.status_code == 200
    assert read.json()["display_name"] == "Synthetic Customer"
    assert read.json()["preferred_location_id"] == location_id
    assert read.json()["email"] == "customer@example.test"

    updated = client.patch("/api/v1/customers/me", headers=headers, json={
        "display_name": "Updated Customer",
        "preferred_language": "en",
        "contact_preference": "phone",
    })
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated Customer"
    assert updated.json()["preferred_language"] == "en"
    assert updated.json()["contact_preference"] == "phone"
    assert client.patch("/api/v1/customers/me", headers=headers, json={"display_name": None}).status_code == 422
    assert client.patch("/api/v1/customers/me", headers=headers, json={"preferred_language": None}).status_code == 422
    assert client.get("/api/v1/customers/me").status_code == 401


def test_customer_registration_rejects_duplicate_normalized_phone_and_invalid_locality() -> None:
    first = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000802",
        "display_name": "First Customer",
        "password": "synthetic-password-802",
    })
    assert first.status_code == 201
    duplicate = client.post("/api/v1/auth/register", json={
        "phone_number": "+251 900 000 802",
        "display_name": "Duplicate Customer",
        "password": "synthetic-password-803",
    })
    assert duplicate.status_code == 409

    invalid = client.post("/api/v1/auth/register", json={
        "phone_number": "+251900000804",
        "display_name": "Invalid Locality Customer",
        "password": "synthetic-password-804",
        "preferred_location_id": "missing-location",
    })
    assert invalid.status_code == 422
    db = TestingSession()
    assert db.query(User).filter_by(phone_number="+251900000804").count() == 0
    db.close()


def test_logout_revokes_existing_access_token() -> None:
    phone = f"+2519{uuid4().int % 10**8:08d}"
    registered = client.post("/api/v1/auth/register", json={
        "phone_number": phone,
        "display_name": "Synthetic Logout Account",
        "password": "synthetic-logout-password",
    })
    assert registered.status_code == 201
    token_response = client.post("/api/v1/auth/login", json={
        "phone_number": phone,
        "password": "synthetic-logout-password",
    })
    assert token_response.status_code == 200
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    assert client.get("/api/v1/customers/me", headers=headers).status_code == 200

    logged_out = client.post("/api/v1/auth/logout", headers=headers)
    assert logged_out.status_code == 204
    assert client.get("/api/v1/customers/me", headers=headers).status_code == 401


def _create_business_test_account(phone: str) -> dict[str, str]:
    registration = client.post("/api/v1/auth/register", json={
        "phone_number": phone,
        "display_name": "Synthetic Business Owner",
        "password": "synthetic-business-password",
    })
    assert registration.status_code == 201
    token = client.post("/api/v1/auth/login", json={
        "phone_number": phone,
        "password": "synthetic-business-password",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_seller_onboarding_creates_business_and_pending_owner_membership() -> None:
    category_id = "00000000-0000-4000-8000-000000000071"
    location_id = "10000000-0000-4000-8000-000000000003"
    db = TestingSession()
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="test-local-produce", name_en="Local produce", is_active=True))
    if db.get(Location, location_id) is None:
        db.add(Location(
            id=location_id, parent_id="10000000-0000-4000-8000-000000000002",
            code="ET-SO-MAALE-KOYBE", level="locality", name_en="Koybe",
            name_am="ቆይቤ", is_active=True,
        ))
    db.commit()
    db.close()

    headers = _create_business_test_account("+251900000971")
    created = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Koybe Produce",
        "business_type": "producer",
        "description": "Synthetic local produce business",
        "primary_category_id": category_id,
        "location_label": "Koybe",
        "operating_location_id": location_id,
        "service_area": ["Koybe", "Jinka"],
        "operating_hours": {"public_note": "Mon-Sat, 08:00-18:00"},
        "supported_languages": ["am", "en"],
        "contact_phone": "+251900000971",
        "publish_contact_phone": False,
    })
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["business_id"]
    assert body["business_type"] == "producer"
    assert body["verification_status"] == "pending"
    assert body["membership_status"] == "pending"
    assert body["public_contact_phone"] is None
    assert body["contact_phone"] == "+251900000971"
    assert body["primary_category_id"] == category_id
    assert body["operating_location_id"] == location_id

    db = TestingSession()
    business = db.get(BusinessProfile, body["business_id"])
    membership = db.query(BusinessMembership).filter_by(
        business_id=body["business_id"],
    ).one()
    assert business is not None
    assert business.legal_name == "Koybe Produce"
    assert business.public_location_visibility == "hidden"
    assert business.latitude is None and business.longitude is None
    assert membership.membership_role == "owner"
    assert membership.status == "pending"
    db.close()

    loaded = client.get("/api/v1/sellers/me", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["business_id"] == body["business_id"]
    assert loaded.json()["service_area"] == ["Koybe", "Jinka"]


def test_seller_can_edit_business_profile_and_must_consent_to_exact_location() -> None:
    headers = _create_business_test_account("+251900000972")
    created = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Synthetic Jinka Shop",
        "location_label": "Jinka",
        "business_type": "shop",
    })
    assert created.status_code == 201, created.text

    denied = client.patch("/api/v1/sellers/me", headers=headers, json={
        "public_location_visibility": "exact",
        "latitude": 6.0,
        "longitude": 36.5,
        "confirm_exact_location": False,
    })
    assert denied.status_code == 422

    updated = client.patch("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Updated Jinka Shop",
        "description": "Updated synthetic business description",
        "contact_email": "shop@example.test",
        "publish_contact_email": True,
        "public_contact_method": "email",
        "service_area": ["Jinka", "Koybe"],
        "public_location_visibility": "exact",
        "latitude": 6.0,
        "longitude": 36.5,
        "confirm_exact_location": True,
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["public_name"] == "Updated Jinka Shop"
    assert updated.json()["public_contact_email"] == "shop@example.test"
    assert updated.json()["public_contact_method"] == "email"
    assert updated.json()["public_location_visibility"] == "exact"

    db = TestingSession()
    business = db.get(BusinessProfile, updated.json()["business_id"])
    assert business.location_consent_at is not None
    assert business.latitude == 6.0 and business.longitude == 36.5
    db.close()


def test_legacy_seller_profile_can_be_upgraded_to_governed_business() -> None:
    headers = _create_business_test_account("+251900000973")
    user = client.get("/api/v1/customers/me", headers=headers)
    assert user.status_code == 200
    db = TestingSession()
    legacy = SellerProfile(
        user_id=user.json()["user_id"],
        public_name="Legacy Seller",
        location_label="Koybe",
    )
    db.add(legacy)
    db.commit()
    db.close()

    upgraded = client.post("/api/v1/sellers/me", headers=headers, json={
        "public_name": "Legacy Seller Updated",
        "location_label": "Koybe",
        "business_type": "individual",
    })
    assert upgraded.status_code == 201, upgraded.text
    assert upgraded.json()["business_id"]
    assert upgraded.json()["membership_status"] == "pending"


def test_customer_profile_photo_upload_read_replace_delete_and_isolation(tmp_path) -> None:
    storage = LocalImageStorage(tmp_path / "private-photos")
    app.dependency_overrides[get_image_storage] = lambda: storage
    try:
        registered = client.post("/api/v1/auth/register", json={
            "phone_number": "+251900000811",
            "display_name": "Photo Buyer",
            "password": "synthetic-photo-password",
        })
        assert registered.status_code == 201
        token = client.post("/api/v1/auth/login", json={
            "phone_number": "+251900000811",
            "password": "synthetic-photo-password",
        }).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        first = BytesIO()
        Image.new("RGB", (24, 24), color=(40, 90, 120)).save(first, format="PNG")
        uploaded = client.post(
            "/api/v1/customers/me/photo",
            headers=headers,
            files={"file": ("profile.png", first.getvalue(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        profile = client.get("/api/v1/customers/me", headers=headers).json()
        assert profile["profile_photo_url"] == "/customers/me/photo"
        assert "profile_photo_key" not in profile

        photo = client.get("/api/v1/customers/me/photo", headers=headers)
        assert photo.status_code == 200
        assert photo.headers["content-type"] == "image/jpeg"
        assert photo.headers["cache-control"] == "private, no-store"

        second = BytesIO()
        Image.new("RGB", (20, 20), color=(10, 20, 30)).save(second, format="JPEG")
        replaced = client.post(
            "/api/v1/customers/me/photo",
            headers=headers,
            files={"file": ("replacement.jpg", second.getvalue(), "image/jpeg")},
        )
        assert replaced.status_code == 201, replaced.text
        assert client.get("/api/v1/customers/me/photo", headers=headers).status_code == 200

        other = client.post("/api/v1/auth/register", json={
            "phone_number": "+251900000812",
            "display_name": "Other Buyer",
            "password": "synthetic-photo-password",
        })
        assert other.status_code == 201
        other_token = client.post("/api/v1/auth/login", json={
            "phone_number": "+251900000812",
            "password": "synthetic-photo-password",
        }).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        assert client.get("/api/v1/customers/me/photo", headers=other_headers).status_code == 404

        deleted = client.delete("/api/v1/customers/me/photo", headers=headers)
        assert deleted.status_code == 204
        assert client.get("/api/v1/customers/me/photo", headers=headers).status_code == 404
    finally:
        app.dependency_overrides.pop(get_image_storage, None)
