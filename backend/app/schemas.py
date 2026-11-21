from pydantic import BaseModel, ConfigDict, Field

class RegisterRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)

class LoginRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=32)
    password: str = Field(min_length=12, max_length=128)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    phone_number: str
    display_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
