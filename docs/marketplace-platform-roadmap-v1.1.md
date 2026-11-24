# South Omo Market — Customer Platform and Geographic Expansion Roadmap

**Controlled scope addendum:** SOM-PLATFORM-ADD-001  
**Version:** 1.1  
**Date:** 2026-11-24  
**Status:** Implementation baseline in progress; not a production-release authorization.

This addendum preserves the approved MVP v1.0 baseline and records the Owner's later direction to complete customer-facing account functionality and include map-based discovery. It does not silently rewrite the original MVP freeze.

## Delivery sequence and acceptance gates

### P0 — Authentication consistency
- Phone-number identity remains the MVP registration identifier.
- Minimum password length is exactly 6 characters across buyer, seller, and API registration/login validation.
- Tests cover five-character rejection and six-character acceptance.
- Passwords remain one-way hashed; never store plaintext.
- Registration must not report success unless the user row is committed and can subsequently be read and authenticated.

### P1 — Complete customer registration and profile
- Required account data: phone number, full/display name, password, preferred town/market, and preferred language (Amharic or English).
- Optional profile data: email, profile photo, and additional contact preference.
- Keep buyer/customer profile data distinct from seller/business onboarding data.
- Seller onboarding collects business/public name, business type/category, operating locality, contact details, and optional map pin; do not force ordinary buyers to create a seller profile.
- Validate and normalize phone numbers; enforce uniqueness; protect private fields.
- Provide profile read/update, account status, logout/session handling, and clear validation/error states.
- Do not invent verification badges or claim phone verification until an actual OTP/verification service is integrated.

### P2 — Customer dashboard
- Account overview and editable profile.
- Saved/favourite listings.
- My inquiries and inquiry status/history.
- Recently viewed listings where privacy-safe.
- Notification preferences and account settings.
- Clear entry points to browse, search, map, saved items, and profile.
- All dashboard data must be retrieved from authenticated API endpoints, not hard-coded demo content.

### P3 — Seller workspace
- Seller/business profile onboarding and editing.
- Create/edit/pause/expire listings with multiple photos, category attributes, price/currency, locality, and optional coordinates.
- Listing status and moderation feedback.
- Inquiry inbox and response workflow.
- Listing performance summary only where backed by stored events.
- Seller dashboard must remain distinct from customer dashboard.

### P4 — Maps and geographic discovery (newly in scope)
- Map/list toggle for marketplace discovery.
- Map pins for listings and recognized markets/towns; pin clustering at wider zoom levels.
- Search/filter map results by category, locality, price, and availability/status.
- Opt-in device location with permission explanation; manual locality selection remains available.
- Store latitude/longitude only when supplied or explicitly selected; retain locality labels for users who decline location sharing.
- Listing detail shows an approximate map location unless the seller explicitly chooses to publish an exact public pin.
- Directions hand-off to an installed map app where supported.
- Handle denied permissions, unavailable GPS, no coordinates, network loss, and empty map results gracefully.
- Use a compliant tile provider and attribution. Do not depend on the public OpenStreetMap community tile server as an unrestricted production tile CDN.
- Consider bounded offline map caching only after licensing, storage, and low-bandwidth behavior are validated.

### P5 — Administration and operations dashboard
- Role-gated overview for customers, sellers, listings, inquiries, reports, moderation, markets/locations, featured placements, and audit events.
- Search/filter/export where justified and permission-controlled.
- Operational KPIs must be computed from persisted records and display their time range.
- Owner/admin actions must be auditable; never expose customer passwords or private authentication data.

### P6 — Marketplace capabilities and resilience
- Guest browsing; phone-based account access; call seller; buyer inquiries; saved listings.
- Categories include livestock, agriculture, food/groceries, shops/products, services, property/equipment.
- Visible/negotiable prices, listing photos, seller profiles, locality selection, expiry, moderation, basic featured ads.
- Offline drafts and a retryable sync queue; show sync state and conflict/error outcomes.
- Notifications, subscriptions, and advertisements can be prepared with clear entitlements and auditability.
- Digital payments, in-app chat, and delivery coordination remain later gated capabilities unless separately prioritized; do not simulate successful payments or delivery.

## Data and persistence requirements

- PostgreSQL is the authoritative shared application store.
- SQLAlchemy models and Alembic migrations must agree; schema changes require migration and rollback/recovery consideration.
- SQLite is for local/offline drafts and queued work only, not a substitute for server account persistence.
- Registration acceptance requires integration evidence for insert, commit, read-after-write, duplicate-phone rejection, and login using the same configured database.
- API readiness must report database connectivity accurately.
- No production migration, deployment, or commercial launch is implied by this implementation addendum.

## Localization, access, and quality
- Amharic is primary; English is secondary. Do not add Maale translations to this product.
- Ethiopian localities and market names should be data-driven and maintainable.
- Accessibility: screen-reader labels, keyboard/focus support where applicable, contrast, scalable text, and touch targets.
- Low-bandwidth behavior: compressed images, pagination, retry states, caching with clear freshness, and graceful fallbacks.
- Synthetic test data only in CI.
- Each phase requires code review, automated tests, exact-HEAD CI evidence, and user/device acceptance where visual or field behavior is involved.

## Current known implementation defects
- Seller mobile password validator previously enforced 12 characters while the API and buyer form accepted 6.
- Customer registration currently persists only phone, display name, and password hash.
- Buyer flow is an inquiry-gating dialog, not a customer dashboard.
- Seller profile currently contains only public name and location label.
- Live database connectivity and end-to-end registration persistence have not yet been proven against the user's deployed runtime.
- No verified map experience or coordinate-backed map discovery is present in the reviewed MVP implementation.
