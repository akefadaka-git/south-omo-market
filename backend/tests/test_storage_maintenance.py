from datetime import datetime, timedelta, timezone

from app.storage_maintenance import select_orphan_keys


def test_orphan_selection_excludes_referenced_recent_and_out_of_scope_objects():
    now = datetime.now(timezone.utc)
    candidates = [
        ("listings/old/orphan.jpg", now - timedelta(days=10)),
        ("listings/old/referenced.jpg", now - timedelta(days=10)),
        ("listings/recent/orphan.jpg", now - timedelta(days=2)),
        ("backups/old.jpg", now - timedelta(days=30)),
        ("listings/../unsafe.jpg", now - timedelta(days=30)),
    ]
    result = select_orphan_keys(
        candidates,
        {"listings/old/referenced.jpg"},
        now - timedelta(days=7),
    )
    assert result == ["listings/old/orphan.jpg"]
