# Free Render + Neon testing deployment

**Status:** non-production testing only. This guide does not authorize production deployment, paid upgrades, or commercial activation.

## Architecture

- API: Render Free Web Service, Python 3.12, Singapore region.
- Database: the Neon Free project South Omo Market, using the isolated south-omo-testing branch in aws-ap-southeast-1.
- PostgreSQL database: neondb.
- ORM and migrations: existing SQLAlchemy 2 + Alembic migrations in backend/migrations/versions.
- Mobile API prefix: /api/v1.

The Render region is Singapore to keep the test API close to the Neon project region.

## Create the Render service

1. Open the Render Dashboard and choose New → Blueprint.
2. Connect the repository akefadaka-git/south-omo-market and select branch feat/a3-platform-foundation.
3. Select the repository root render.yaml.
4. Confirm that the service plan is Free and the region is Singapore.
5. During initial Blueprint creation, Render prompts for the two variables marked sync: false. Supply the connection strings for the Neon south-omo-testing branch as described below.
6. Review the Blueprint and create the service only when ready. autoDeployTrigger is off, so subsequent Git pushes will not automatically deploy it.

Do not create a Render PostgreSQL database. The database is already hosted on Neon.

## Neon connection strings

In the Neon Console, open project South Omo Market, select branch south-omo-testing, database neondb, and its database owner role. Use the Connect dialog:

- DATABASE_URL: turn connection pooling on. The hostname must contain -pooler. This is for normal API requests.
- DATABASE_URL_UNPOOLED: turn connection pooling off. The hostname must not contain -pooler. This is for Alembic migrations.

Keep sslmode=require (or stricter) in both URLs. Enter the values directly into Render's secret environment-variable prompts. Never commit either connection string, paste it into source code, or share it in chat.

The application normalizes Neon's standard postgresql:// URLs to SQLAlchemy's installed psycopg 3 driver. Alembic explicitly prefers DATABASE_URL_UNPOOLED and rejects a pooled hostname.

Render generates JWT_SECRET automatically through the Blueprint. Do not replace it with a public or hardcoded value.

## Migration and health-check behavior

Render Free web services do not support preDeployCommand. For this test service, the start command therefore runs:

1. alembic upgrade head using the direct Neon URL.
2. uvicorn app.main:app on Render's injected PORT.

If the migration fails, the API process does not start. Alembic's version table makes repeated startup checks idempotent after the database reaches the current migration head. This service must point only to south-omo-testing, never the production branch.

- GET /health is a liveness check and does not require the database.
- GET /ready is a readiness check and returns HTTP 503 if SELECT 1 cannot reach the database. Render uses /ready.
- Initial API smoke tests: /health, /ready, /api/v1/categories, /api/v1/locations, and /api/v1/listings.

## Android build against the hosted test API

After Render creates the service, copy its public HTTPS hostname (not a secret). Build the Android APK from mobile/:

    flutter build apk --release --split-per-abi \
      --dart-define=API_BASE_URL=https://<render-service>.onrender.com/api/v1

The default 10.0.2.2 URL is only for Android emulators. A physical phone must use the Render HTTPS URL in the build-time API_BASE_URL define.

## Free-tier limitations and test-data rules

- Render Free services sleep after inactivity and may take time to wake. The first request after sleep can be slow.
- Render Free filesystems are ephemeral. This Blueprint deliberately uses local image storage only for disposable tests; uploaded images may be lost on restart or redeploy.
- Rate limiting uses in-memory storage in this testing environment. It is not shared across instances.
- Use synthetic accounts, listings, contact details, and images only. Do not load real customer or shareholder information.
- Do not treat this setup as production-ready. Persistent object storage, shared rate limiting, backup/restore, security/privacy review, SMS ownership verification, and operational monitoring remain separate gates.
- Do not upgrade any service or enable paid resources. No Render service is created until the Blueprint is explicitly applied in the Render Dashboard.
