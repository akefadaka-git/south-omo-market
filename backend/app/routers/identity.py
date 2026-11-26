from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.dependencies import get_current_user
from app.models import CustomerProfile, Location, Market, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import hash_password, issue_access_token, verify_password

router = APIRouter(prefix="/auth")


def normalize_phone_number(value: str) -> str:
    """Normalize Ethiopian mobile-number variants to the E.164 +251 format.

    Accepts 0916546488, 916546488, 25916546488, +251916546488,
    and 00251916546488. Validation is provider-neutral for Ethiopian
    mobile lines, including Safaricom numbers.
    """
    compact = "".join(char for char in value.strip() if char not in " -().")
    if not compact or any(not (char.isdigit() or char == "+") for char in compact):
        raise HTTPException(status_code=422, detail="Phone number format is invalid")
    if compact.count("+") > 1 or ("+" in compact and not compact.startswith("+")):
        raise HTTPException(status_code=422, detail="Phone number format is invalid")
    digits = compact[1:] if compact.startswith("+") else compact
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in {"0"} and digits[1] in {"7", "9"}:
        digits = "251" + digits[1:]
    elif len(digits) == 9 and digits[0] in {"7", "9"}:
        digits = "251" + digits
    elif len(digits) == 11 and digits.startswith("25"):
        digits = "251" + digits[2:]
    if len(digits) != 12 or not digits.startswith(("2517", "2519")):
        raise HTTPException(status_code=422, detail="Phone number format is invalid")
    return "+" + digits


def validate_preferred_references(db: Session, location_id: str | None, market_id: str | None) -> None:
    if location_id is not None:
        location = db.get(Location, location_id)
        if location is None or not location.is_active:
            raise HTTPException(status_code=422, detail="Preferred locality must be an active location")
    if market_id is not None:
        market = db.get(Market, market_id)
        if market is None or not market.is_active:
            raise HTTPException(status_code=422, detail="Preferred market must be active")
        if location_id is not None and market.location_id not in (None, location_id):
            raise HTTPException(status_code=422, detail="Preferred market does not belong to the selected locality")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def register(request: Request, response: Response, payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    phone_number = normalize_phone_number(payload.phone_number)
    validate_preferred_references(db, payload.preferred_location_id, payload.preferred_market_id)
    if db.scalar(select(User).where(User.phone_number == phone_number)):
        raise HTTPException(status_code=409, detail="Phone number is already registered")
    user = User(phone_number=phone_number, display_name=payload.display_name,
                account_type=payload.account_type,
                password_hash=hash_password(payload.password))
    profile = CustomerProfile(
        user=user,
        preferred_location_id=payload.preferred_location_id,
        preferred_market_id=payload.preferred_market_id,
        preferred_language=payload.preferred_language,
        email=payload.email,
    )
    db.add_all([user, profile])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Phone number is already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    phone_number = normalize_phone_number(payload.phone_number)
    user = db.scalar(select(User).where(User.phone_number == phone_number))
    if user is None or not user.is_active or user.is_suspended or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=issue_access_token(user.id, user.auth_version))



@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Revoke every outstanding access token for this account."""
    user.auth_version += 1
    db.add(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
