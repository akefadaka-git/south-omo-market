# Image storage operations: backup, restore and orphan cleanup

This runbook is an A3 operational control. It is not evidence that production backups have been configured or that a recovery exercise has succeeded.

## Required production controls

- Use a private, dedicated application image bucket. Block public access at the account and bucket level; the application API is the publication gate.
- Use a separate backup bucket in a separate administrative/security boundary where the provider supports it. Enable bucket versioning and a retention policy; consider Object Lock/WORM controls for the required retention period.
- Give the runtime identity only the minimum read/write permissions for the application bucket. Give the backup identity read access to the source and write access to the backup bucket. Keep restore permissions separately controlled.
- Protect BACKUP_PASSPHRASE_FILE outside the repository and application web root. Keep a recovery copy under owner-controlled access. Never commit credentials or passphrases.
- Back up PostgreSQL and image objects as one coordinated recovery point. Pause marketplace writes during the snapshot window so the database and object inventory are consistent.
- Store backups in a different failure domain from the primary database and image bucket. Monitor job success, age of last successful backup, and available capacity.

## Encrypted backup

The script backend/scripts/backup_restore.sh requires pg_dump, aws CLI, gpg, psql, and pg_restore.

Set DATABASE_URL, S3_BUCKET, BACKUP_S3_BUCKET, BACKUP_S3_PREFIX, and BACKUP_PASSPHRASE_FILE. S3_BUCKET and BACKUP_S3_BUCKET must differ. Set S3_ENDPOINT_URL only when the selected provider requires a custom S3 endpoint.

1. Pause listing writes and uploads (maintenance mode).
2. Run: bash backend/scripts/backup_restore.sh backup
3. Record the emitted backup ID and verify the manifest, encrypted database dump and object prefix exist in the separate backup bucket.
4. Resume writes only after the backup command and remote object checks succeed.

The script creates a PostgreSQL custom-format dump, encrypts it with GPG AES-256, records a SHA-256 checksum in a manifest, copies listing objects to the backup bucket, and uploads the manifest last. The backup bucket objects use server-side AES-256 encryption. The script does not configure provider versioning, lifecycle retention, replication or Object Lock; configure those at the provider.

## Restore drill

Restore only to a newly provisioned, empty PostgreSQL database and an empty listings/ prefix in the target image bucket. Set RESTORE_DATABASE_URL and the exact BACKUP_ID, retain the backup-bucket variables, and run:

    bash backend/scripts/backup_restore.sh restore

The script verifies the decrypted database dump checksum and refuses a non-empty database or image prefix. It never drops or cleans an existing database and never uses destructive object sync. After restore, run Alembic/current-schema checks, compare listing-image metadata against object keys, fetch representative images through the API, and document RPO/RTO. Do not route production traffic until the owner approves the recovery result.

## Orphan image cleanup

Run the scanner from backend/ with the production environment loaded:

    python -m app.storage_maintenance --min-age-days 7

The default is a dry run. It compares object keys/files under listings/ against listing_images.storage_key, and selects only unreferenced JPEG objects older than the grace period. Review the complete output and investigate every candidate before deletion. The minimum accepted grace period is seven days.

Deletion requires an explicit second invocation:

    python -m app.storage_maintenance --min-age-days 7 --apply

The command never deletes database rows, never scans outside listings/, and refuses path traversal candidates. Do not automate --apply until the dry-run report is reviewed and the operational owner has approved a recurring cleanup policy. Keep database backups and object versioning/retention enabled before enabling deletion.

## Evidence and outstanding work

- Automated tests cover candidate selection and prove referenced, recent, and out-of-scope objects are excluded.
- The orphan scanner is not run against production data; no real object was deleted.
- The backup/restore script is syntax-checked in CI, but no provider credentials, production bucket, backup passphrase, or target restore database are configured in this repository.
- No backup or restore exercise has been executed. Production provider-specific integration, access policy, encryption/key custody, retention, monitoring, and measured recovery objectives remain operational gates.
- The S3 SDK contract test uses Moto; it does not verify the selected production provider.
