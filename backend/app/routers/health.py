from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.database import get_engine

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check; deliberately does not require a database connection."""
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> dict[str, str]:
    """Readiness check used by the host to verify the database is reachable."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "database": "ok"}
