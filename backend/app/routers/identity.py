from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User
from app.schemas import RegisterRequest, UserResponse
from app.security import hash_password

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.phone_number == payload.phone_number)):
        raise HTTPException(status_code=409, detail="Phone number is already registered")
    user = User(phone_number=payload.phone_number, display_name=payload.display_name,
                password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
