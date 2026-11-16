from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401

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
