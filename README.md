# South Omo Market

Amharic-first, Maale-enabled local classified marketplace for buyers, sellers, traders and businesses in South Omo, Ethiopia.

MVP geography: Koybe and Jinka. Sellers publish listings; buyers discover and contact sellers directly. Initial settlement is cash/direct seller payment.

Excluded: wallets, escrow, cryptocurrency, loans, delivery fleet, complex GPS, social feed, AI recommendations, nationwide expansion and complex payment systems.

Stack: Flutter Android + SQLite local drafts; FastAPI modular monolith; PostgreSQL; SQLAlchemy 2; Alembic; React + TypeScript admin; versioned REST/OpenAPI.

Repository layout: backend/ API; mobile/ Flutter client; admin/ moderation console; docs/ decisions and controls.

Development uses synthetic data only. Hosting, SMS/OTP, object storage and payment providers remain unselected. No repository license has been granted. Maale terminology and translations require human review before release. Physical market validation is mandatory before commercial launch. Deployment and commercial activation require separate owner approval.

This is an implementation foundation, not a production-ready marketplace.


## Listing photos and offline drafts (A3)

- The API accepts JPEG, PNG and WebP uploads for seller-owned draft listings only.
- Each upload is decoded and verified, EXIF orientation is applied, and the image is re-encoded as JPEG before storage. The configured defaults are 5 MiB per upload, five images per listing and 20 megapixels per image.
- Uploads use a client-generated UUID. Repeating an upload with the same UUID for the same listing returns the existing image record, making mobile retries safe.
- Pending-review and rejected listings do not expose image bytes. Image retrieval is served through the API only after a listing is published.
- `ListingImageStorage` is the provider-neutral storage contract. The local adapter writes to a private directory with restrictive permissions. An S3-compatible adapter is available through the boto3 API client; no production provider or credentials are selected.
- Local storage is selected by default. Configure `IMAGE_STORAGE_BACKEND=s3`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY` to select object storage. Optional settings are `S3_REGION` (default `us-east-1`), `S3_ENDPOINT_URL` (for a compatible endpoint), and `S3_USE_SSL` (default `true`; disable only for local test emulators). Keep the bucket private; the application does not make objects public and serves images through its publication-gated API endpoint.
- If using local storage in production, configure `IMAGE_STORAGE_DIR` to an absolute, persistent, private volume outside the web root. Configure the reverse proxy/request body limit to match or exceed the application upload limit. Production startup rejects a relative local-storage path.
- The mobile client stores drafts and queued photos in app-private storage. It assigns stable UUID idempotency keys, syncs drafts before photos when the seller workspace opens online or connectivity returns, and retries safely after interrupted network requests. Server sync creates a draft only; it does not publish or bypass moderation.
- Legacy local drafts are retained during the SQLite schema upgrade. They receive a stable sync UUID and must be assigned an A1 category before they can sync.

Verification includes synthetic API tests for image decoding/normalization, size and per-listing limits, unpublished-image privacy, image retry idempotency, offline draft replay/conflict handling, and SQLite migration upgrade/downgrade. CI also runs the complete Alembic chain against PostgreSQL 16, verifies the append-only audit trigger rejects UPDATE and DELETE, and exercises the S3 adapter with Moto's S3 API emulator. Moto verifies SDK/API contract behavior; it does not replace testing against the eventual production object-storage provider. Production bucket policy, credentials, backups, lifecycle/retention and restore remain unconfigured and require separate verification.
