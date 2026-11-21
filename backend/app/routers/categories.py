from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category

router = APIRouter(prefix="/categories")


def _category_payload(row: Category, lang: str) -> dict[str, object]:
    translated = row.name_am if lang == "am" else row.name_mdy if lang == "mdy" else row.name_en
    return {
        "id": row.id,
        "slug": row.slug,
        "parent_id": row.parent_id,
        "name": translated or row.name_en,
        "name_en": row.name_en,
        "name_am": row.name_am,
        "name_mdy": row.name_mdy,
        "is_leaf": not any(child.parent_id == row.id for child in getattr(row, "_active_children", [])),
        "attributes_schema": row.attributes_schema or [],
    }


@router.get("")
def list_categories(
    lang: str = Query(default="en", pattern="^(en|am|mdy)$"),
    parent_id: str | None = None,
    roots_only: bool = False,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = select(Category).where(Category.is_active.is_(True))
    if roots_only:
        query = query.where(Category.parent_id.is_(None))
    elif parent_id is not None:
        query = query.where(Category.parent_id == parent_id)
    rows = db.scalars(query.order_by(Category.name_en, Category.id)).all()
    parent_ids = {row.parent_id for row in rows if row.parent_id is not None}
    # Mark whether each returned category has active children without N+1 queries.
    child_ids = set(db.scalars(
        select(Category.parent_id).where(
            Category.is_active.is_(True), Category.parent_id.is_not(None)
        )
    ).all())
    result = []
    for row in rows:
        translated = row.name_am if lang == "am" else row.name_mdy if lang == "mdy" else row.name_en
        result.append({
            "id": row.id,
            "slug": row.slug,
            "parent_id": row.parent_id,
            "name": translated or row.name_en,
            "name_en": row.name_en,
            "name_am": row.name_am,
            "name_mdy": row.name_mdy,
            "is_leaf": row.id not in child_ids,
            "attributes_schema": row.attributes_schema or [],
        })
    return result
