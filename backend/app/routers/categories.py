from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Category

router = APIRouter(prefix="/categories")

@router.get("")
def list_categories(db: Session = Depends(get_db)) -> list[dict[str, str]]:
    rows = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name_en)).all()
    return [{"id": row.id, "slug": row.slug, "name": row.name_en} for row in rows]
