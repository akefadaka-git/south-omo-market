from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.main import app
from app.routers import health


def test_health_is_available_without_database() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    monkeypatch.setattr(health, "get_engine", lambda: engine)
    try:
        response = TestClient(app).get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok"}
    finally:
        engine.dispose()


def test_readiness_fails_when_database_is_unavailable(monkeypatch) -> None:
    def unavailable():
        raise RuntimeError("synthetic connection failure")

    monkeypatch.setattr(health, "get_engine", unavailable)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
