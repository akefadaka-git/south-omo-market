from functools import lru_cache
from pathlib import Path

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
    image_storage_dir: Path = Path("var/listing-images")
    max_listing_image_bytes: int = 5 * 1024 * 1024
    max_listing_images: int = 5
    max_listing_image_pixels: int = 20_000_000

    @model_validator(mode="after")
    def reject_development_secret_in_production(self):
        secret = self.jwt_secret.get_secret_value()
        if self.app_env == "production" and (
            secret == "development-only-change-this-secret" or len(secret) < 32
        ):
            raise ValueError("Production requires a separately generated JWT_SECRET of 32+ characters")
        if self.app_env == "production" and not self.image_storage_dir.is_absolute():
            raise ValueError("Production requires an absolute IMAGE_STORAGE_DIR on persistent private storage")
        if self.max_listing_image_bytes < 1 or self.max_listing_images < 1:
            raise ValueError("Image upload limits must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
