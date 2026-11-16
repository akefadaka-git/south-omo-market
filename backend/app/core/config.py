from functools import lru_cache

from pydantic import SecretStr, model_validator
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

    @model_validator(mode="after")
    def reject_development_secret_in_production(self):
        secret = self.jwt_secret.get_secret_value()
        if self.app_env == "production" and (
            secret == "development-only-change-this-secret" or len(secret) < 32
        ):
            raise ValueError("Production requires a separately generated JWT_SECRET of 32+ characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
