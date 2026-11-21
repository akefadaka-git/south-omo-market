from fastapi import FastAPI
from app.core.config import get_settings
from app.routers import admin, categories, health, identity, inquiries, listings, locations, reports, sellers
from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(health.router, tags=["health"])
app.include_router(identity.router, prefix=settings.api_v1_prefix, tags=["identity"])
app.include_router(categories.router, prefix=settings.api_v1_prefix, tags=["categories"])
app.include_router(locations.router, prefix=settings.api_v1_prefix, tags=["locations"])
app.include_router(sellers.router, prefix=settings.api_v1_prefix, tags=["sellers"])
app.include_router(listings.router, prefix=settings.api_v1_prefix, tags=["listings"])
app.include_router(inquiries.router, prefix=settings.api_v1_prefix, tags=["inquiries"])
app.include_router(reports.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
