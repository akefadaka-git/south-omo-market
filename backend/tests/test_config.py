import pytest
from pydantic import SecretStr

from app.core.config import Settings


def production_s3_settings(**overrides):
    values = {
        "app_env": "production",
        "jwt_secret": SecretStr("x" * 48),
        "image_storage_backend": "s3",
        "s3_bucket": "private-market-images",
        "s3_access_key_id": "synthetic-access-key",
        "s3_secret_access_key": SecretStr("synthetic-secret"),
    }
    values.update(overrides)
    return values


def test_production_s3_requires_tls() -> None:
    with pytest.raises(ValueError, match="S3_USE_SSL=true"):
        Settings(**production_s3_settings(s3_use_ssl=False))


def test_production_s3_rejects_http_endpoint() -> None:
    with pytest.raises(ValueError, match="must use HTTPS"):
        Settings(**production_s3_settings(s3_endpoint_url="http://objects.example.test"))


def test_production_s3_accepts_https_endpoint() -> None:
    settings = Settings(**production_s3_settings(
        s3_endpoint_url="https://objects.example.test"
    ))
    assert settings.s3_use_ssl is True
