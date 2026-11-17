from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.core.config import get_settings


class ListingImageStorage(Protocol):
    def save_jpeg(self, listing_id: str, data: bytes) -> str: ...
    def resolve(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...


class LocalImageStorage:
    """Private filesystem adapter; production requires a persistent, non-web-root volume."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or get_settings().image_storage_dir).expanduser().resolve()

    def save_jpeg(self, listing_id: str, data: bytes) -> str:
        key = f"listings/{listing_id}/{uuid4().hex}.jpg"
        destination = self._resolve(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        try:
            with temporary.open("xb") as output:
                output.write(data)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return key

    def resolve(self, key: str) -> Path:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError("Stored image not found")
        return path

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)

    def _resolve(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return candidate
