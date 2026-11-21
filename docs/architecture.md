# Approved architecture v1.0

Owner-approved during A2. Provider selections remain deferred.

A modular monolith API serves one Flutter Android client and one React administration client. No MVP microservices.

| Layer | Technology |
|---|---|
| Android | Flutter / Dart |
| Offline drafts | SQLite |
| API | FastAPI / Python |
| Persistence | PostgreSQL |
| ORM / migrations | SQLAlchemy 2 / Alembic |
| Admin | React / TypeScript / Vite |
| Contract | OpenAPI |
| Media | Provider-neutral object storage boundary; provider not selected |

Domains: Identity and access; Sellers; Catalog; Listings; Geography and discovery; Inquiries and trust & safety; Monetization (dormant pending validation).

Planned entities: users, sessions, seller profiles, business profiles, locations, categories, listings, listing images and attributes, saved listings, inquiries, subscription plans, seller subscriptions, advertisements, moderation reports and audit events. Migrate only entities needed by implemented use cases.

API prefix /api/v1. Use JSON, UUID identifiers, UTC timestamps, server-side ownership checks and idempotency keys for retryable writes.

Offline drafts are local-only until server acceptance. Distinguish draft, pending, synchronized and failed states. Server controls public visibility and moderation.

Deferred: hosting/region, SMS/OTP vendor, object-storage vendor and payment provider. Cash/direct seller payment remains the MVP model.
