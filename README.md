# South Omo Market

Amharic-first, Maale-enabled local classified marketplace for buyers, sellers, traders and businesses in South Omo, Ethiopia.

MVP geography: Koybe and Jinka. Sellers publish listings; buyers discover and contact sellers directly. Initial settlement is cash/direct seller payment.

Excluded: wallets, escrow, cryptocurrency, loans, delivery fleet, complex GPS, social feed, AI recommendations, nationwide expansion and complex payment systems.

Stack: Flutter Android + SQLite local drafts; FastAPI modular monolith; PostgreSQL; SQLAlchemy 2; Alembic; React + TypeScript admin; versioned REST/OpenAPI.

Repository layout: backend/ API; mobile/ Flutter client; admin/ moderation console; docs/ decisions and controls.

Development uses synthetic data only. Hosting, SMS/OTP, object storage and payment providers remain unselected. No repository license has been granted. Maale terminology and translations require human review before release. Physical market validation is mandatory before commercial launch. Deployment and commercial activation require separate owner approval.

This is an implementation foundation, not a production-ready marketplace.
