from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app
from app.models import Category, User

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(engine)
category_id = "00000000-0000-4000-8000-000000000001"
with TestingSession() as db:
    if db.get(Category, category_id) is None:
        db.add(Category(id=category_id, slug="livestock", name_en="Livestock", is_active=True))
        db.commit()


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def register_and_login(phone: str, display: str) -> str:
    created = client.post("/api/v1/auth/register", json={
        "phone_number": phone,
        "display_name": display,
        "password": "synthetic-test-password-123",
    })
    assert created.status_code == 201
    response = client.post("/api/v1/auth/login", json={
        "phone_number": phone,
        "password": "synthetic-test-password-123",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


def test_only_admin_can_approve_pending_listing() -> None:
    seller_token = register_and_login("+251900000101", "Synthetic Seller")
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    profile = client.post("/api/v1/sellers/me", headers=seller_headers, json={
        "public_name": "Test Livestock Seller",
        "location_label": "Koybe",
    })
    assert profile.status_code == 201
    created = client.post("/api/v1/listings", headers=seller_headers, json={
        "category_id": category_id,
        "title": "Synthetic cattle for moderation",
        "description": "Synthetic moderation test",
        "price_minor": 100000,
        "location_label": "Koybe",
    })
    assert created.status_code == 201
    listing_id = created.json()["id"]
    submitted = client.post(f"/api/v1/listings/{listing_id}/submit", headers=seller_headers)
    assert submitted.status_code == 200

    forbidden = client.get("/api/v1/admin/moderation/queue", headers=seller_headers)
    assert forbidden.status_code == 403

    admin_token = register_and_login("+251900000102", "Synthetic Admin")
    admin_user = TestingSession()
    admin = admin_user.query(User).filter_by(phone_number="+251900000102").one()
    admin.is_admin = True
    admin_user.commit()
    admin_user.close()
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
    public = client.get(f"/api/v1/listings/{listing_id}")
    assert public.status_code == 200
