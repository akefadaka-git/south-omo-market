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
        "rate_limit_storage_uri": "rediss://rate-limit.example.test:6379/0",
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


def test_production_rejects_process_local_rate_limit_storage() -> None:
    with pytest.raises(ValueError, match="shared Redis"):
        Settings(**production_s3_settings(rate_limit_storage_uri="memory://"))


def test_neon_urls_use_psycopg_and_direct_migrations() -> None:
    settings = Settings(
        database_url="postgresql://app:poolpass@ep-test-pooler.neon.tech/neondb?sslmode=require",
        database_url_unpooled=SecretStr(
            "postgresql://app:directpass@ep-test.neon.tech/neondb?sslmode=require"
        ),
    )
    assert settings.sqlalchemy_database_url() == (
        "postgresql+psycopg://app:poolpass@ep-test-pooler.neon.tech/neondb?sslmode=require"
    )
    assert settings.sqlalchemy_database_url(for_migrations=True) == (
        "postgresql+psycopg://app:directpass@ep-test.neon.tech/neondb?sslmode=require"
    )


def test_migrations_reject_pooled_neon_url() -> None:
    settings = Settings(
        database_url="postgresql://app:poolpass@ep-test-pooler.neon.tech/neondb"
    )
    with pytest.raises(ValueError, match="direct DATABASE_URL_UNPOOLED"):
        settings.sqlalchemy_database_url(for_migrations=True)


def test_sqlite_database_url_is_preserved() -> None:
    settings = Settings(database_url="sqlite:///./test.db")
    assert settings.sqlalchemy_database_url() == "sqlite:///./test.db"
