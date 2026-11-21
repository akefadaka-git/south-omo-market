# Production readiness checklist

This checklist is a deployment handoff aid. Completing the document does not mean a production environment exists or has passed verification.

## API ingress and upload limits

- Terminate HTTPS at a managed load balancer or reverse proxy with a valid certificate and automatic renewal.
- Permit only HTTPS from clients; redirect or reject plain HTTP.
- Set the proxy request-body limit to at least 6 MiB to allow multipart framing around the API's 5 MiB image payload limit. Keep application-level byte and pixel validation enabled.
- Example Nginx location (adapt paths and upstream to the selected deployment):

      client_max_body_size 6m;
      proxy_request_buffering on;
      proxy_pass http://south_omo_market_api;

- Do not expose the API worker port directly to the public internet.
- Ensure the API sees the trusted proxy peer address. Do not trust arbitrary client-supplied X-Forwarded-For values for rate-limit identity.

## Runtime configuration

- Set APP_ENV=production and generate a unique JWT_SECRET of at least 32 characters.
- Set DATABASE_URL to a managed PostgreSQL database with TLS and least-privilege credentials.
- Set RATE_LIMIT_STORAGE_URI to a private Redis endpoint (rediss:// where supported). Production startup rejects memory://.
- Set IMAGE_STORAGE_BACKEND=s3 only after the provider confirms that application objects, replicas, logs and backups are stored in Ethiopia. The Personal Data Protection Proclamation No. 1321/2024, Article 22(1), requires local personal data to be stored on a server/data centre in Ethiopia. Cloudflare R2 has no published Ethiopia location and is not approved for production personal data. Do not route real user media to an offshore free tier without a written legal/Authority determination.
- Do not store secrets in source control, public build variables, or application logs.

## Object storage

- Verify physical data location in Ethiopia for primary data, replicas, backups, support access and logs before storing any locally collected personal data. Keep the current Singapore test environment synthetic-only.
- Block public access at the account and bucket level.
- Require TLS for object API requests and enable provider-side encryption at rest.
- Use separate least-privilege identities for application access, backup and restore.
- Enable versioning and retention on the backup bucket. Keep it in a separate administrative/security boundary.
- Test the actual provider's consistency, pagination, multipart behavior, lifecycle rules and IAM policies.

## Backup and recovery

- Define owner-approved RPO and RTO.
- Schedule coordinated PostgreSQL and object backups with marketplace writes paused during the snapshot.
- Alert on failed backups, stale backup age, low capacity and missing manifests.
- Keep the GPG passphrase under independent owner-controlled recovery custody.
- Perform a restore drill into an isolated, empty database and image bucket. Verify database migrations, object SHA-256 inventory, listing-image references and API image reads.
- Record the backup ID, checksums, measured RPO/RTO, operator, evidence and approval before considering recovery verified.

## Cleanup and monitoring

- Run orphan cleanup in dry-run mode first; review the exact candidate list with writes/uploads paused.
- Deletion requires separate operational approval and the explicit --apply option.
- Monitor API 4xx/5xx rates, authentication and inquiry throttling, database health, Redis health, storage capacity and upload failures.
- Retain application logs and security/audit records according to an approved retention policy.

## Release gates

- Complete legal/privacy/data-protection review and security review before production personal data.
- Complete human Maale language review.
- Complete mandatory physical market validation before commercial launch.
- A4 verification does not authorize merge or deployment. A5 requires separate owner approval.
