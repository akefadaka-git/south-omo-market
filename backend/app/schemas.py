from pydantic import BaseModel, ConfigDict, Field, field_validator

class RegisterRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    preferred_location_id: str | None = None
    preferred_market_id: str | None = None
    preferred_language: str = Field(default="am", pattern="^(am|en)$")
    email: str | None = Field(default=None, max_length=254)
    account_type: str = Field(default="buyer", pattern="^(buyer|merchant|bulk_distributor|producer|service_provider|other)$")

    @field_validator("display_name")
    @classmethod
    def display_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Display name cannot be blank")
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value and value.strip() else None

class LoginRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32)
    password: str = Field(min_length=6, max_length=128)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    phone_number: str
    display_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CustomerProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    preferred_location_id: str | None = None
    preferred_market_id: str | None = None
    preferred_language: str | None = Field(default=None, pattern="^(am|en)$")
    email: str | None = Field(default=None, max_length=254)
    contact_preference: str | None = Field(default=None, pattern="^(phone|sms|email)$")

    @field_validator("display_name")
    @classmethod
    def display_name_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Display name cannot be blank")
        return value.strip() if value is not None else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value and value.strip() else None
