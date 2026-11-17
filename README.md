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
- `ListingImageStorage` is the provider-neutral storage contract. The current development adapter writes to a private local directory with restrictive permissions; a production S3-compatible adapter and credentials are deliberately not selected.
- Configure `IMAGE_STORAGE_DIR` to an absolute, persistent, private volume in production. Keep it outside the web root and configure the reverse proxy/request body limit to match or exceed the application upload limit. Production startup rejects a relative image-storage path.
- The mobile client stores drafts and queued photos in app-private storage. It assigns stable UUID idempotency keys, syncs drafts before photos, and retries safely after interrupted network requests. Server sync creates a draft only; it does not publish or bypass moderation.
- Legacy local drafts are retained during the SQLite schema upgrade. They receive a stable sync UUID and must be assigned an A1 category before they can sync.

Verification currently includes synthetic API tests for image decoding/normalization, size and per-listing limits, unpublished-image privacy, image retry idempotency, offline draft replay/conflict handling, and SQLite migration upgrade/downgrade. PostgreSQL migration and production object-storage integration still require separate A4 verification.
