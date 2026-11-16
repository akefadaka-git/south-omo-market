from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401
from app.models import Category

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)


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
        db.add(Category(id=category_id, slug="test-livestock", name_en="Test livestock", is_active=True))
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

    created = client.post("/api/v1/listings", headers=headers, json={
        "category_id": category_id,
        "title": "Synthetic cattle listing",
        "description": "Test-only listing",
        "price_minor": 125000,
        "location_label": "Koybe",
    })
    assert created.status_code == 201
    listing_id = created.json()["id"]

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
