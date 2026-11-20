from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category

router = APIRouter(prefix="/categories")


@router.get("")
def list_categories(
    lang: str = Query(default="en", pattern="^(en|am|mdy)$"),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    rows = db.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.name_en)
    ).all()
    result = []
    for row in rows:
        translated = row.name_am if lang == "am" else row.name_mdy if lang == "mdy" else row.name_en
        result.append({
            "id": row.id, "slug": row.slug, "name": translated or row.name_en,
            "name_en": row.name_en, "name_am": row.name_am, "name_mdy": row.name_mdy,
        })
    return result
