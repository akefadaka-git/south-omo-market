#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ACTION="${1:-}"
if [[ "$ACTION" != "backup" && "$ACTION" != "restore" ]]; then
  echo "Usage: $0 backup|restore" >&2
  exit 2
fi

: "${S3_BUCKET:?Set S3_BUCKET to the application image bucket}"
: "${BACKUP_S3_BUCKET:?Set BACKUP_S3_BUCKET to a separate backup bucket}"
: "${BACKUP_S3_PREFIX:?Set BACKUP_S3_PREFIX to a restricted backup prefix}"
: "${BACKUP_PASSPHRASE_FILE:?Set BACKUP_PASSPHRASE_FILE to a protected GPG passphrase file}"
[[ "$BACKUP_S3_PREFIX" =~ ^[A-Za-z0-9._/-]+$ && "$BACKUP_S3_PREFIX" != /* && "$BACKUP_S3_PREFIX" != *".."* ]] || {
  echo "BACKUP_S3_PREFIX must be a safe relative object prefix." >&2; exit 2;
}
[[ "$S3_BUCKET" != "$BACKUP_S3_BUCKET" ]] || {
  echo "Application and backup buckets must be different." >&2; exit 2;
}
[[ -r "$BACKUP_PASSPHRASE_FILE" ]] || {
  echo "Backup passphrase file is not readable." >&2; exit 2;
}

aws_args=()
if [[ -n "${S3_ENDPOINT_URL:-}" ]]; then
  aws_args+=(--endpoint-url "$S3_ENDPOINT_URL")
fi

pg_url() {
  printf '%s' "$1" | sed 's#^postgresql+psycopg://#postgresql://#'
}

# Write relative object key, byte length and SHA-256 of the object content.
# listing_prefix identifies the keys to inventory; content_prefix identifies
# the corresponding object bytes (which may be in the separate backup bucket).
write_object_inventory() {
  local listing_bucket="$1" listing_prefix="$2"
  local content_bucket="$3" content_prefix="$4" output="$5"
  aws "${aws_args[@]}" s3api list-objects-v2 --bucket "$listing_bucket" \
    --prefix "$listing_prefix" --query 'Contents[].Key' --output text \
    | tr '\t' '\n' \
    | while IFS= read -r key; do
        [[ -n "$key" && "$key" != "None" ]] || continue
        [[ "$key" == "$listing_prefix"* ]] || {
          echo "Unexpected object key outside inventory prefix." >&2; exit 2;
        }
        relative="${key#"$listing_prefix"}"
        [[ "$relative" =~ ^[A-Za-z0-9._/-]+$ && "$relative" != *".."* ]] || {
          echo "Unsupported object key in image inventory." >&2; exit 2;
        }
        size="$(aws "${aws_args[@]}" s3api head-object --bucket "$listing_bucket" \
          --key "$key" --query ContentLength --output text)"
        checksum="$(aws "${aws_args[@]}" s3 cp "s3://$content_bucket/$content_prefix$relative" - \
          --only-show-errors | sha256sum | awk '{print $1}')"
        [[ "$checksum" =~ ^[a-f0-9]{64}$ ]] || {
          echo "Could not checksum image object $relative." >&2; exit 2;
        }
        printf '%s\t%s\t%s\n' "$relative" "$size" "$checksum"
      done | sort > "$output"
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
remote="s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX"

if [[ "$ACTION" == "backup" ]]; then
  : "${DATABASE_URL:?Set DATABASE_URL for the source PostgreSQL database}"
  export BACKUP_ID="${BACKUP_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
  [[ "$BACKUP_ID" =~ ^[A-Za-z0-9._-]+$ ]] || {
    echo "BACKUP_ID contains unsupported characters." >&2; exit 2;
  }

  existing_backup_objects="$(aws "${aws_args[@]}" s3api list-objects-v2 \
    --bucket "$BACKUP_S3_BUCKET" --prefix "$BACKUP_S3_PREFIX/$BACKUP_ID/" \
    --max-keys 1 --query 'length(Contents || `[]`)' --output text)"
  [[ "$existing_backup_objects" == "0" ]] || {
    echo "Backup ID already exists in the backup bucket; refusing to overwrite." >&2; exit 2;
  }

  # Quiesce marketplace writes before running this command for a consistent DB/object snapshot.
  pg_dump --format=custom --no-owner --no-acl --dbname="$(pg_url "$DATABASE_URL")" \
    --file="$tmp/database.dump"
  dump_sha="$(sha256sum "$tmp/database.dump" | awk '{print $1}')"
  gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" \
    --symmetric --cipher-algo AES256 --output "$tmp/database.dump.gpg" "$tmp/database.dump"

  aws "${aws_args[@]}" s3 cp "$tmp/database.dump.gpg" \
    "$remote/$BACKUP_ID/database.dump.gpg" --sse AES256 --only-show-errors
  aws "${aws_args[@]}" s3 sync "s3://$S3_BUCKET/listings/" \
    "$remote/$BACKUP_ID/objects/" --sse AES256 --only-show-errors
  write_object_inventory "$S3_BUCKET" "listings/" "$BACKUP_S3_BUCKET" \
    "$BACKUP_S3_PREFIX/$BACKUP_ID/objects/" "$tmp/objects.tsv"
  object_count="$(wc -l < "$tmp/objects.tsv" | tr -d ' ')"
  objects_sha="$(sha256sum "$tmp/objects.tsv" | awk '{print $1}')"
  aws "${aws_args[@]}" s3 cp "$tmp/objects.tsv" \
    "$remote/$BACKUP_ID/objects.tsv" --sse AES256 --only-show-errors

  cat > "$tmp/manifest.txt" <<MANIFEST
backup_id=$BACKUP_ID
created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
source_bucket=$S3_BUCKET
database_dump_sha256=$dump_sha
object_count=$object_count
objects_manifest_sha256=$objects_sha
repository_commit=${GITHUB_SHA:-unknown}
MANIFEST
  aws "${aws_args[@]}" s3 cp "$tmp/manifest.txt" \
    "$remote/$BACKUP_ID/manifest.txt" --sse AES256 --only-show-errors
  echo "Backup completed: $remote/$BACKUP_ID/"
  echo "Database dump encrypted with GPG AES-256; backup objects use server-side AES-256."
  exit 0
fi

: "${BACKUP_ID:?Set BACKUP_ID to the exact backup to restore}"
: "${RESTORE_DATABASE_URL:?Set RESTORE_DATABASE_URL to a newly provisioned empty database}"
[[ "$BACKUP_ID" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "BACKUP_ID contains unsupported characters." >&2; exit 2;
}
if [[ -n "${DATABASE_URL:-}" && "$RESTORE_DATABASE_URL" == "$DATABASE_URL" ]]; then
  echo "Restore target must differ from DATABASE_URL." >&2; exit 2;
fi
aws "${aws_args[@]}" s3 cp "$remote/$BACKUP_ID/manifest.txt" "$tmp/manifest.txt" --only-show-errors
aws "${aws_args[@]}" s3 cp "$remote/$BACKUP_ID/database.dump.gpg" \
  "$tmp/database.dump.gpg" --only-show-errors
aws "${aws_args[@]}" s3 cp "$remote/$BACKUP_ID/objects.tsv" \
  "$tmp/objects.tsv" --only-show-errors
expected_objects_sha="$(sed -n 's/^objects_manifest_sha256=//p' "$tmp/manifest.txt")"
actual_objects_sha="$(sha256sum "$tmp/objects.tsv" | awk '{print $1}')"
[[ "$expected_objects_sha" =~ ^[a-f0-9]{64}$ && "$actual_objects_sha" == "$expected_objects_sha" ]] || {
  echo "Object inventory checksum mismatch; restore aborted." >&2; exit 2;
}
expected_object_count="$(sed -n 's/^object_count=//p' "$tmp/manifest.txt")"
[[ "$expected_object_count" =~ ^[0-9]+$ && "$expected_object_count" == "$(wc -l < "$tmp/objects.tsv" | tr -d ' ')" ]] || {
  echo "Object inventory count mismatch; restore aborted." >&2; exit 2;
}
expected_sha="$(sed -n 's/^database_dump_sha256=//p' "$tmp/manifest.txt")"
[[ "$expected_sha" =~ ^[a-f0-9]{64}$ ]] || {
  echo "Backup manifest checksum is missing or malformed." >&2; exit 2;
}
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$BACKUP_PASSPHRASE_FILE" \
  --decrypt --output "$tmp/database.dump" "$tmp/database.dump.gpg"
actual_sha="$(sha256sum "$tmp/database.dump" | awk '{print $1}')"
[[ "$actual_sha" == "$expected_sha" ]] || {
  echo "Database backup checksum mismatch; restore aborted." >&2; exit 2;
}

# Never drop/clean a database. Restore only into a newly provisioned empty database.
table_count="$(psql "$(pg_url "$RESTORE_DATABASE_URL")" -Atqc \
  "SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema' AND c.relkind IN ('r','p','v','m','S','f')) + (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema')) + (SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('information_schema','public'))")"
[[ "$table_count" == "0" ]] || {
  echo "Restore target database is not empty; restore aborted." >&2; exit 2;
}
aws "${aws_args[@]}" s3api head-bucket --bucket "$S3_BUCKET"
object_count="$(aws "${aws_args[@]}" s3api list-objects-v2 --bucket "$S3_BUCKET" \
  --prefix listings/ --max-keys 1 --query 'length(Contents || `[]`)' --output text)"
[[ "$object_count" == "0" ]] || {
  echo "Restore target image prefix is not empty; restore aborted." >&2; exit 2;
}

pg_restore --no-owner --no-privileges --exit-on-error \
  --dbname="$(pg_url "$RESTORE_DATABASE_URL")" "$tmp/database.dump"
aws "${aws_args[@]}" s3 sync "$remote/$BACKUP_ID/objects/" \
  "s3://$S3_BUCKET/listings/" --only-show-errors
write_object_inventory "$S3_BUCKET" "listings/" "$S3_BUCKET" \
  "listings/" "$tmp/restored-objects.tsv"
if ! diff -u "$tmp/objects.tsv" "$tmp/restored-objects.tsv"; then
  echo "Restored image-object inventory differs from the backup manifest." >&2
  exit 2
fi
echo "Restore completed into the supplied empty database and image prefix."
echo "Run application-level integrity checks before routing any traffic."
