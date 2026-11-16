from fastapi import FastAPI
from app.core.config import get_settings
from app.routers import health, identity

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(health.router, tags=["health"])
app.include_router(identity.router, prefix=settings.api_v1_prefix, tags=["identity"])

@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
