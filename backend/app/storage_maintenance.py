"""Conservative orphan-image scanner. Deletion requires --apply and a seven-day minimum age."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_engine
from app.core.image_storage import LocalImageStorage, S3ImageStorage, get_image_storage
from app.models import ListingImage


def select_orphan_keys(
    candidates: list[tuple[str, datetime]],
    referenced_keys: set[str],
    cutoff: datetime,
) -> list[str]:
    """Return unreferenced objects older than cutoff; callers must separately authorize deletion."""
    normalized_cutoff = cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=timezone.utc)
    return sorted(
        key for key, modified in candidates
        if key not in referenced_keys
        and (modified if modified.tzinfo else modified.replace(tzinfo=timezone.utc)) <= normalized_cutoff
        and key.startswith("listings/")
        and ".." not in Path(key).parts
    )


def _referenced_keys() -> set[str]:
    with get_engine().connect() as connection:
        return set(connection.scalars(select(ListingImage.storage_key)).all())


def _s3_candidates(storage: S3ImageStorage) -> list[tuple[str, datetime]]:
    paginator = storage.client.get_paginator("list_objects_v2")
    candidates: list[tuple[str, datetime]] = []
    for page in paginator.paginate(Bucket=storage.bucket, Prefix="listings/"):
        for item in page.get("Contents", []):
            candidates.append((item["Key"], item["LastModified"]))
    return candidates


def _local_candidates(storage: LocalImageStorage) -> list[tuple[str, datetime]]:
    candidates: list[tuple[str, datetime]] = []
    listings = storage.root / "listings"
    if not listings.exists():
        return candidates
    for path in listings.rglob("*.jpg"):
        if path.is_file():
            key = path.relative_to(storage.root).as_posix()
            candidates.append((key, datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-age-days", type=int, default=7)
    parser.add_argument("--apply", action="store_true", help="Delete candidates; default is dry-run")
    args = parser.parse_args()
    if args.min_age_days < 7:
        parser.error("--min-age-days cannot be less than 7 days")

    storage = get_image_storage()
    referenced = _referenced_keys()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.min_age_days)
    if isinstance(storage, S3ImageStorage):
        candidates = _s3_candidates(storage)
    elif isinstance(storage, LocalImageStorage):
        candidates = _local_candidates(storage)
    else:
        raise RuntimeError("Unsupported image storage adapter; refusing cleanup")

    orphans = select_orphan_keys(candidates, referenced, cutoff)
    print(f"Referenced image records: {len(referenced)}")
    print(f"Orphan candidates older than {args.min_age_days} days: {len(orphans)}")
    for key in orphans:
        print(f"{'DELETE' if args.apply else 'DRY-RUN'} {key}")
    if args.apply:
        for key in orphans:
            storage.delete(key)
        print(f"Deleted {len(orphans)} orphan object(s).")
    else:
        print("Dry run only. Re-run with --apply after reviewing this exact candidate list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
