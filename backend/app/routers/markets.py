from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.dependencies import require_admin
from app.models import AuditEvent, Location, Market, MarketScheduleDay, User

router = APIRouter(prefix="/markets")
admin_router = APIRouter(prefix="/admin/markets")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class MarketCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    location_id: str | None = None

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Market name cannot be blank")
        return value.strip()


class MarketUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    location_id: str | None = None

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Market name cannot be blank")
        return value.strip() if value is not None else None


class ScheduleUpdate(BaseModel):
    days: list[int] = Field(max_length=7)
    effective_from: date | None = None
    effective_until: date | None = None

    @field_validator("days")
    @classmethod
    def unique_valid_days(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate weekdays are not allowed")
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("Weekdays must be between 0 (Monday) and 6 (Sunday)")
        return sorted(value)


class MarketStatusUpdate(BaseModel):
    is_active: bool


def _market_query(active_only: bool):
    statement = select(Market).options(selectinload(Market.schedule_days))
    if active_only:
        statement = statement.where(Market.is_active.is_(True))
    return statement.order_by(Market.name, Market.code)


def _serialize_market(market: Market, db: Session, lang: str = "en") -> dict[str, object]:
    location = db.get(Location, market.location_id) if market.location_id else None
    location_payload = None
    if location is not None:
        localized = location.name_am if lang == "am" else location.name_mdy if lang == "mdy" else location.name_en
        location_payload = {
            "id": location.id, "name": localized or location.name_en,
            "name_en": location.name_en, "name_am": location.name_am,
            "name_mdy": location.name_mdy,
        }
    return {
        "id": market.id, "code": market.code, "name": market.name,
        "description": market.description,
        "location_id": market.location_id, "location": location_payload,
        "is_active": market.is_active,
        "schedule_days": sorted(day.weekday for day in market.schedule_days if day.is_active),
        "schedule_entries": [{"weekday": day.weekday, "is_active": day.is_active, "effective_from": day.effective_from.isoformat() if day.effective_from else None, "effective_until": day.effective_until.isoformat() if day.effective_until else None} for day in market.schedule_days],
    }


def _get_market(db: Session, market_id: str, active_only: bool = False) -> Market:
    statement = select(Market).options(selectinload(Market.schedule_days)).where(Market.id == market_id)
    if active_only:
        statement = statement.where(Market.is_active.is_(True))
    market = db.scalar(statement)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


def _validate_location(db: Session, location_id: str | None) -> None:
    if location_id is None:
        return
    location = db.get(Location, location_id)
    if location is None or not location.is_active:
        raise HTTPException(status_code=422, detail="An active geographic location is required")


@router.get("")
def list_markets(
    lang: Literal["en", "am", "mdy"] = Query(default="en"),
    q: str | None = Query(default=None, max_length=120),
    weekday: int | None = Query(default=None, ge=0, le=6),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    markets = db.scalars(_market_query(True)).all()
    needle = q.strip().casefold() if q else ""
    return [
        _serialize_market(row, db, lang) for row in markets
        if (not needle or needle in row.name.casefold() or needle in row.code.casefold()
            or needle in (row.description or "").casefold())
        and (weekday is None or any(day.weekday == weekday and day.is_active for day in row.schedule_days))
    ]


@router.get("/schedule")
def weekly_schedule(
    lang: Literal["en", "am", "mdy"] = Query(default="en"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    markets = db.scalars(_market_query(True)).all()
    days = []
    for weekday, weekday_name in enumerate(WEEKDAYS):
        scheduled = [
            _serialize_market(market, db, lang)
            for market in markets
            if any(day.weekday == weekday and day.is_active for day in market.schedule_days)
        ]
        days.append({"weekday": weekday, "weekday_name": weekday_name, "markets": scheduled})
    return {"timezone": "Africa/Addis_Ababa", "days": days}


@router.get("/by-day/{weekday}")
def markets_by_day(
    weekday: int = Path(ge=0, le=6),
    lang: Literal["en", "am", "mdy"] = Query(default="en"),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    markets = db.scalars(_market_query(True)).all()
    return [
        _serialize_market(market, db, lang)
        for market in markets
        if any(day.weekday == weekday and day.is_active for day in market.schedule_days)
    ]


@router.get("/{market_id}")
def market_detail(
    market_id: str,
    lang: Literal["en", "am", "mdy"] = Query(default="en"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _serialize_market(_get_market(db, market_id, active_only=True), db, lang)


@admin_router.get("")
def admin_list_markets(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return [_serialize_market(row, db) for row in db.scalars(_market_query(False)).all()]


@admin_router.post("", status_code=201)
def create_market(
    payload: MarketCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _validate_location(db, payload.location_id)
    if db.scalar(select(Market.id).where(Market.code == payload.code)) is not None:
        raise HTTPException(status_code=409, detail="Market code already exists")
    market = Market(code=payload.code, name=payload.name.strip(), description=payload.description, location_id=payload.location_id)
    db.add(market)
    db.flush()
    db.add(AuditEvent(
        actor_id=admin.id, action="market.created", resource_type="market",
        resource_id=market.id, event_metadata={"code": market.code, "name": market.name},
    ))
    db.commit()
    return _serialize_market(_get_market(db, market.id), db)


@admin_router.patch("/{market_id}")
def update_market(
    market_id: str,
    payload: MarketUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    market = _get_market(db, market_id)
    changes = payload.model_dump(exclude_unset=True)
    if "location_id" in changes:
        _validate_location(db, changes["location_id"])
    before = {"name": market.name, "description": market.description, "location_id": market.location_id}
    for key, value in changes.items():
        if key == "name" and value is not None:
            value = value.strip()
        setattr(market, key, value)
    if changes:
        db.add(AuditEvent(
            actor_id=admin.id, action="market.updated", resource_type="market",
            resource_id=market.id, event_metadata={"before": before, "after": changes},
        ))
    db.commit()
    return _serialize_market(_get_market(db, market.id), db)


@admin_router.put("/{market_id}/schedule")
def update_market_schedule(
    market_id: str,
    payload: ScheduleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    market = _get_market(db, market_id)
    before = sorted(day.weekday for day in market.schedule_days if day.is_active)
    selected = set(payload.days)
    existing = {day.weekday: day for day in market.schedule_days}
    for weekday, schedule_day in existing.items():
        schedule_day.is_active = weekday in selected
        if weekday in selected:
            schedule_day.effective_from = payload.effective_from
            schedule_day.effective_until = payload.effective_until
    for weekday in selected - set(existing):
        market.schedule_days.append(MarketScheduleDay(weekday=weekday, is_active=True, effective_from=payload.effective_from, effective_until=payload.effective_until))
    db.add(AuditEvent(
        actor_id=admin.id, action="market.schedule.updated", resource_type="market",
        resource_id=market.id, event_metadata={"before": before, "after": sorted(selected), "effective_from": payload.effective_from.isoformat() if payload.effective_from else None, "effective_until": payload.effective_until.isoformat() if payload.effective_until else None},
    ))
    db.commit()
    return _serialize_market(_get_market(db, market.id), db)


@admin_router.patch("/{market_id}/status")
def update_market_status(
    market_id: str,
    payload: MarketStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    market = _get_market(db, market_id)
    previous = market.is_active
    market.is_active = payload.is_active
    db.add(AuditEvent(
        actor_id=admin.id, action="market.status.updated", resource_type="market",
        resource_id=market.id, event_metadata={"before": previous, "after": market.is_active},
    ))
    db.commit()
    return _serialize_market(_get_market(db, market.id), db)

 
@admin_router.get("/audit")
def market_audit_history(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.resource_type == "market")
        .order_by(desc(AuditEvent.created_at), desc(AuditEvent.id))
        .limit(limit)
    ).all()
    return [{
        "id": event.id, "actor_id": event.actor_id, "action": event.action,
        "resource_type": event.resource_type, "resource_id": event.resource_id,
        "metadata": event.event_metadata, "created_at": event.created_at.isoformat(),
    } for event in events]
