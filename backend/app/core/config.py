from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    app_name: str = "South Omo Market API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://localhost/south_omo_market"
    jwt_secret: SecretStr = SecretStr("development-only-change-this-secret")
    jwt_issuer: str = "south-omo-market"
    access_token_minutes: int = 30

@lru_cache
def get_settings() -> Settings:
    return Settings()
