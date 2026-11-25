from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import get_settings
from app.routers import admin, businesses, categories, commerce, customers, employment, health, identity, inquiries, listings, locations, markets, reports, sellers
from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "validation_error",
        429: "rate_limited",
    }.get(status_code, "request_failed")


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    field_errors: dict[str, list[str]] = {}
    for error in exc.errors():
        field = ".".join(str(part) for part in error.get("loc", ()) if part != "body") or "request"
        field_errors.setdefault(field, []).append(str(error.get("msg", "Invalid value")))
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error": {
                "code": "validation_error",
                "message": "One or more fields need attention.",
                "field_errors": field_errors,
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exc: StarletteHTTPException,
) -> JSONResponse:
    message = str(exc.detail) if isinstance(exc.detail, str) else "The request could not be completed."
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "detail": exc.detail,
            "error": {
                "code": _error_code(exc.status_code),
                "message": message,
                "field_errors": {},
            },
        },
    )
app.include_router(health.router, tags=["health"])
app.include_router(identity.router, prefix=settings.api_v1_prefix, tags=["identity"])
app.include_router(customers.router, prefix=settings.api_v1_prefix, tags=["customers"])
app.include_router(categories.router, prefix=settings.api_v1_prefix, tags=["categories"])
app.include_router(locations.router, prefix=settings.api_v1_prefix, tags=["locations"])
app.include_router(markets.router, prefix=settings.api_v1_prefix, tags=["markets"])
app.include_router(markets.admin_router, prefix=settings.api_v1_prefix, tags=["admin-markets"])
app.include_router(sellers.router, prefix=settings.api_v1_prefix, tags=["sellers"])
app.include_router(listings.router, prefix=settings.api_v1_prefix, tags=["listings"])
app.include_router(inquiries.router, prefix=settings.api_v1_prefix, tags=["inquiries"])
app.include_router(reports.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(employment.router, prefix=settings.api_v1_prefix, tags=["employment-agency"])
app.include_router(businesses.router, prefix=settings.api_v1_prefix, tags=["businesses"])
app.include_router(commerce.router, prefix=settings.api_v1_prefix, tags=["commerce"])


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
