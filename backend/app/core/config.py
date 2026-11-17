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
    image_storage_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_use_ssl: bool = True
    max_listing_image_bytes: int = 5 * 1024 * 1024
    max_listing_images: int = 5
    max_listing_image_pixels: int = 20_000_000

    @model_validator(mode="after")
    def validate_runtime_settings(self):
        secret = self.jwt_secret.get_secret_value()
        if self.app_env == "production" and (
            secret == "development-only-change-this-secret" or len(secret) < 32
        ):
            raise ValueError("Production requires a separately generated JWT_SECRET of 32+ characters")
        if self.image_storage_backend not in {"local", "s3"}:
            raise ValueError("IMAGE_STORAGE_BACKEND must be local or s3")
        if self.app_env == "production" and self.image_storage_backend == "local" and not self.image_storage_dir.is_absolute():
            raise ValueError("Production local storage requires an absolute persistent private IMAGE_STORAGE_DIR")
        if self.image_storage_backend == "s3" and not all((
            self.s3_bucket, self.s3_access_key_id, self.s3_secret_access_key
        )):
            raise ValueError("S3 storage requires S3_BUCKET, S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY")
        if min(self.max_listing_image_bytes, self.max_listing_images, self.max_listing_image_pixels) < 1:
            raise ValueError("Image upload limits must be positive")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
