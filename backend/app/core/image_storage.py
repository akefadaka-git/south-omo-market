from pathlib import Path
from typing import Protocol
from uuid import uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings


class ListingImageStorage(Protocol):
    def save_jpeg(self, listing_id: str, data: bytes) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalImageStorage:
    """Private filesystem adapter for development and single-node deployments."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().image_storage_dir).expanduser().resolve()

    def save_jpeg(self, listing_id: str, data: bytes) -> str:
        key = f"listings/{listing_id}/{uuid4().hex}.jpg"
        destination = self._resolve(key)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination.parent.chmod(0o700)
        temporary = destination.with_suffix(".tmp")
        try:
            with temporary.open("xb") as output:
                output.write(data)
            temporary.chmod(0o600)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return key

    def read(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError("Stored image not found")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def _resolve(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return candidate


class S3ImageStorage:
    """S3-compatible private object adapter. The bucket must deny public access."""

    def __init__(
        self,
        *,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        use_ssl: bool = True,
        client=None,
    ) -> None:
        self.bucket = bucket
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            use_ssl=use_ssl,
            config=BotoConfig(
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def save_jpeg(self, listing_id: str, data: bytes) -> str:
        key = f"listings/{listing_id}/{uuid4().hex}.jpg"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType="image/jpeg",
            Metadata={"listing-id": listing_id},
        )
        return key

    def read(self, key: str) -> bytes:
        self._validate_key(key)
        try:
            result = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise FileNotFoundError("Stored image not found") from error
            raise
        return result["Body"].read()

    def delete(self, key: str) -> None:
        self._validate_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)

    @staticmethod
    def _validate_key(key: str) -> None:
        path = Path(key)
        if path.is_absolute() or ".." in path.parts or not key.startswith("listings/"):
            raise ValueError("Invalid storage key")


def get_image_storage() -> ListingImageStorage:
    settings = get_settings()
    if settings.image_storage_backend == "s3":
        assert settings.s3_bucket is not None
        assert settings.s3_access_key_id is not None
        assert settings.s3_secret_access_key is not None
        return S3ImageStorage(
            bucket=settings.s3_bucket,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key.get_secret_value(),
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            use_ssl=settings.s3_use_ssl,
        )
    return LocalImageStorage()
