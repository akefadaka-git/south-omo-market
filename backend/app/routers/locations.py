from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Location

router = APIRouter(prefix="/locations")


@router.get("")
def list_locations(
    parent_id: str | None = None,
    level: str | None = Query(default=None, pattern="^(zone|woreda|town|locality)$"),
    lang: str = Query(default="en", pattern="^(en|am|mdy)$"),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    query = select(Location).where(Location.is_active.is_(True))
    if parent_id is not None:
        query = query.where(Location.parent_id == parent_id)
    if level is not None:
        query = query.where(Location.level == level)
    rows = db.scalars(query.order_by(Location.name_en)).all()
    result = []
    for row in rows:
        translated = row.name_am if lang == "am" else row.name_mdy if lang == "mdy" else row.name_en
        result.append({
            "id": row.id, "parent_id": row.parent_id, "code": row.code, "level": row.level,
            "name": translated,
            "translation_complete": bool(row.name_en and row.name_am), "name_en": row.name_en,
            "name_am": row.name_am, "name_mdy": row.name_mdy,
        })
    return result
