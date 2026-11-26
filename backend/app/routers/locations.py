from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import AuditEvent, Location, User

router = APIRouter(prefix="/locations")
admin_router = APIRouter(prefix="/admin/locations")

LOCATION_TAGS = {
    "product", "service", "market", "transport", "health", "education",
    "agriculture", "tourism", "public_service", "finance", "other",
}
LOCATION_LEVELS = {"zone", "woreda", "town", "locality"}


class LocationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z0-9-]+$")
    level: Literal["zone", "woreda", "town", "locality"]
    parent_id: str | None = None
    name_en: str = Field(min_length=1, max_length=120)
    name_am: str = Field(min_length=1, max_length=120)
    description_en: str | None = Field(default=None, max_length=4000)
    description_am: str | None = Field(default=None, max_length=4000)
    address_en: str | None = Field(default=None, max_length=500)
    address_am: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name_en", "name_am")
    @classmethod
    def nonblank_names(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("English and Amharic location names are required")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, values: list[str]) -> list[str]:
        normalized = sorted(set(values))
        invalid = set(normalized) - LOCATION_TAGS
        if invalid:
            raise ValueError(f"Unsupported location tags: {', '.join(sorted(invalid))}")
        return normalized

    @model_validator(mode="after")
    def validate_pairs(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together")
        if (self.address_en or self.address_am) and not (self.address_en and self.address_am):
            raise ValueError("Addresses must be supplied in both English and Amharic")
        return self


class LocationUpdate(BaseModel):
    parent_id: str | None = None
    level: Literal["zone", "woreda", "town", "locality"] | None = None
    name_en: str | None = Field(default=None, min_length=1, max_length=120)
    name_am: str | None = Field(default=None, min_length=1, max_length=120)
    description_en: str | None = Field(default=None, max_length=4000)
    description_am: str | None = Field(default=None, max_length=4000)
    address_en: str | None = Field(default=None, max_length=500)
    address_am: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tags: list[str] | None = Field(default=None, max_length=20)

    @field_validator("name_en", "name_am")
    @classmethod
    def nonblank_names(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Location names cannot be blank")
        return value.strip() if value is not None else None

    @field_validator("tags")
    @classmethod
    def valid_tags(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = sorted(set(values))
        invalid = set(normalized) - LOCATION_TAGS
        if invalid:
            raise ValueError(f"Unsupported location tags: {', '.join(sorted(invalid))}")
        return normalized


class LocationStatusUpdate(BaseModel):
    is_active: bool


def _validate_parent(
    db: Session, parent_id: str | None, level: str, location_id: str | None = None,
) -> None:
    if level == "zone" and parent_id is not None:
        raise HTTPException(status_code=422, detail="A zone cannot have a parent location")
    if level != "zone" and parent_id is None:
        raise HTTPException(status_code=422, detail="A parent location is required below zone level")
    if parent_id is None:
        return
    parent = db.get(Location, parent_id)
    if parent is None or not parent.is_active:
        raise HTTPException(status_code=422, detail="Parent location must exist and be active")
    if parent_id == location_id:
        raise HTTPException(status_code=422, detail="A location cannot be its own parent")
    rank = {"zone": 0, "woreda": 1, "town": 1, "locality": 2}
    if rank[parent.level] >= rank[level]:
        raise HTTPException(status_code=422, detail="Parent location must be at a higher geographic level")
    ancestor_id = parent.parent_id
    visited = {location_id} if location_id else set()
    while ancestor_id:
        if ancestor_id in visited:
            raise HTTPException(status_code=422, detail="Location hierarchy cannot contain a cycle")
        visited.add(ancestor_id)
        ancestor = db.get(Location, ancestor_id)
        ancestor_id = ancestor.parent_id if ancestor else None


def _serialize(row: Location, lang: str = "en") -> dict[str, object]:
    translated = row.name_am if lang == "am" else row.name_mdy if lang == "mdy" else row.name_en
    return {
        "id": row.id,
        "parent_id": row.parent_id,
        "code": row.code,
        "level": row.level,
        "name": translated or row.name_en,
        "name_en": row.name_en,
        "name_am": row.name_am,
        "name_mdy": row.name_mdy,
        "description_en": row.description_en,
        "description_am": row.description_am,
        "address_en": row.address_en,
        "address_am": row.address_am,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "tags": row.tags or [],
        "translation_complete": bool(row.name_en and row.name_am),
        "is_active": row.is_active,
    }


@router.get("")
def list_locations(
    parent_id: str | None = None,
    level: str | None = Query(default=None, pattern="^(zone|woreda|town|locality)$"),
    lang: str = Query(default="en", pattern="^(en|am|mdy)$"),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = select(Location).where(Location.is_active.is_(True))
    if parent_id is not None:
        query = query.where(Location.parent_id == parent_id)
    if level is not None:
        query = query.where(Location.level == level)
    rows = db.scalars(query.order_by(Location.name_en)).all()
    return [_serialize(row, lang) for row in rows]


@admin_router.get("")
def admin_list_locations(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    rows = db.scalars(select(Location).order_by(Location.level, Location.name_en)).all()
    return [_serialize(row) for row in rows]


@admin_router.post("", status_code=201)
def create_location(
    payload: LocationCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.scalar(select(Location.id).where(Location.code == payload.code)) is not None:
        raise HTTPException(status_code=409, detail="Location code already exists")
    _validate_parent(db, payload.parent_id, payload.level)
    row = Location(**payload.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditEvent(
        actor_id=admin.id,
        action="location.created",
        resource_type="location",
        resource_id=row.id,
        event_metadata={"code": row.code, "name_en": row.name_en, "name_am": row.name_am, "tags": row.tags},
    ))
    db.commit()
    db.refresh(row)
    return _serialize(row)


@admin_router.patch("/{location_id}")
def update_location(
    location_id: str,
    payload: LocationUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    row = db.get(Location, location_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    changes = payload.model_dump(exclude_unset=True)
    next_level = changes.get("level", row.level)
    next_parent = changes.get("parent_id", row.parent_id)
    _validate_parent(db, next_parent, next_level, row.id)
    next_en = changes.get("name_en", row.name_en)
    next_am = changes.get("name_am", row.name_am)
    if not next_en or not next_am:
        raise HTTPException(status_code=422, detail="Both English and Amharic location names are required")
    next_latitude = changes.get("latitude", row.latitude)
    next_longitude = changes.get("longitude", row.longitude)
    if (next_latitude is None) != (next_longitude is None):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be supplied together")
    next_address_en = changes.get("address_en", row.address_en)
    next_address_am = changes.get("address_am", row.address_am)
    if (next_address_en or next_address_am) and not (next_address_en and next_address_am):
        raise HTTPException(status_code=422, detail="Addresses must be supplied in both English and Amharic")
    before = _serialize(row)
    for key, value in changes.items():
        setattr(row, key, value)
    db.add(AuditEvent(
        actor_id=admin.id,
        action="location.updated",
        resource_type="location",
        resource_id=row.id,
        event_metadata={"before": before, "after": changes},
    ))
    db.commit()
    db.refresh(row)
    return _serialize(row)


@admin_router.patch("/{location_id}/status")
def update_location_status(
    location_id: str,
    payload: LocationStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    row = db.get(Location, location_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    previous = row.is_active
    row.is_active = payload.is_active
    db.add(AuditEvent(
        actor_id=admin.id,
        action="location.status.updated",
        resource_type="location",
        resource_id=row.id,
        event_metadata={"before": previous, "after": row.is_active},
    ))
    db.commit()
    db.refresh(row)
    return _serialize(row)
