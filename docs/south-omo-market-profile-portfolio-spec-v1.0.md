# South Omo Market — Account, Business Profile and Portfolio Specification

**Controlled scope addendum:** SOM-PLATFORM-ADD-002  
**Version:** 1.0  
**Date:** 2026-11-25  
**Status:** Product scope approved for staged implementation; not a merge, deployment, payment, or commercial-launch authorization.

This addendum preserves MVP v1.0 and SOM-PLATFORM-ADD-001 v1.1. It records the Owner's direction to complete P1 account requirements and extend the product with strong customer profiles, seller/business profiles, and public seller portfolios. Delivery remains staged and evidence-gated.

## 1. Product quality objective

Build a dependable, accessible, low-bandwidth, Amharic-first marketplace for South Omo that earns trust through useful local discovery, accurate listings, responsive seller workflows, transparent moderation, and reliable account controls. Do not claim a market ranking, verification, popularity, or performance level without measurable independent evidence.

## 2. Customer account and profile

### Required account capabilities
- Phone-number identity with normalization and uniqueness enforcement.
- Full/display name, password (minimum 6 characters under the existing MVP contract), preferred town/locality, preferred market, and preferred language (Amharic or English).
- Password hashing, rate-limited authentication, server-side logout/token revocation, session-expiry handling, and account active/suspended status.
- Read/update own profile only; no exposure of password hashes, access tokens, private contact data, or internal moderation data.
- Clear field-level validation, recoverable network errors, retry states, and confirmation of saved changes.

### Optional profile capabilities
- Profile photo with safe image type/size/dimension validation, private upload authorization, replacement/deletion, and persistent object storage.
- Email and preferred contact method.
- Notification preferences when notification delivery is implemented.
- Saved listings, inquiry history, recently viewed items, and account data/export/delete requests in their respective later delivery gates.

### Privacy rules
- Buyers are not required to become sellers or publish a public profile.
- Private profile fields remain private by default.
- Public display name and any public contact channel require explicit publication choice.
- Do not reveal exact buyer location or device coordinates to sellers.
- Account deletion and retention behavior must be defined against legal, fraud-prevention, and audit requirements before activation.

## 3. Seller and business onboarding

A seller account remains a user account with a separately managed seller/business profile. Onboarding must not silently convert every buyer into a seller.

### Seller profile fields
- Public shop/business name.
- Business type and primary category; optional additional categories.
- Business description/about text.
- Operating town/locality, with optional more precise map pin only after explicit opt-in.
- Public phone/contact channel and contact preference.
- Optional email, logo/profile photo, cover photo, and business gallery.
- Operating days/hours and temporary closure status.
- Languages supported and service area.
- Optional registration details collected only where operationally justified; sensitive registration evidence must never be public by default.

### Business lifecycle
- Draft → submitted/pending review → approved/active, or changes requested/rejected/suspended.
- The platform must distinguish account authentication from business verification.
- A seller may publish only within the permissions and moderation status granted to that seller/business.
- Verification status is generated only by a real, auditable review process. Never display a verified badge for unreviewed data.
- Where a business has multiple staff, access is role-based and scoped to the business; ownership transfer and staff revocation must be auditable.

## 4. Public seller portfolio

A portfolio is the public-facing presentation of a seller/business, separate from the user's private account profile.

### Portfolio sections
1. Business identity: public name, logo, short description, business type/category, and locality.
2. About/story: owner-authored description with length limits and safe text rendering.
3. Products and services: live published listings only, with category, price/negotiable state, availability, and freshness.
4. Photo gallery: multiple optimized images with captions, ordering, moderation, and seller ownership controls.
5. Service area: locality labels and optional approximate public map location; exact coordinates only with explicit seller consent.
6. Operating information: days/hours, temporary closure, and last-updated timestamp.
7. Contact actions: call or other enabled contact channel, subject to seller privacy settings.
8. Trust and safety: moderation status and factual verification state only; report business/listing and block seller where supported.

### Portfolio quality requirements
- Fast first render on low-end Android devices and weak networks.
- Paginated listing/gallery content; compressed responsive images and thumbnail-first loading.
- Amharic-first typography and layout with English fallback.
- Shareable public portfolio route with a stable, non-sensitive identifier.
- Accessible controls, meaningful image descriptions, readable contrast, scalable text, and minimum 48dp touch targets.
- Empty states that help new sellers complete onboarding without fabricated sample content.
- No fake reviews, ratings, transaction counts, badges, follower counts, or popularity scores.

### Later trust enhancements (separate gates)
- Buyer reviews only after a defensible transaction or verified-inquiry basis, abuse controls, moderation, and dispute/appeal rules exist.
- Seller response-time metrics only from persisted, consent-appropriate events and with clear measurement windows.
- Follower/subscription features only with privacy controls, abuse prevention, and notification preferences.
- Sponsored/featured placement must be clearly labelled and auditable.

## 5. Delivery sequence and acceptance

### P1 completion — immediate gate
- P1.1: server-side logout/session revocation and client sign-out/expired-session handling.
- P1.2: complete seller onboarding fields and editable seller profile using existing business governance and membership controls where appropriate.
- P1.3: optional customer profile photo only if secure object-storage upload, authorization, deletion/replacement, and tests can be completed without weakening P1.
- P1.4: seller profile edit/read, account status handling, field validation, privacy checks, localization, and regression tests.
- P1.5: exact-HEAD CI, PostgreSQL integration, security checks, and user/device acceptance checklist.
- P1 closes only after all required criteria pass; a successful CI run alone does not close physical-device acceptance.

### Subsequent product phases — not a reason to skip P1
- Customer dashboard: saved listings, inquiries/history, recently viewed, settings, and notifications.
- Seller workspace: portfolio editor, listing lifecycle, multi-photo gallery, inquiry inbox, and persisted performance analytics.
- Marketplace discovery: maps, map/list toggle, locality filters, approximate locations, and safe directions hand-off.
- Trust and safety: reporting, moderation, business verification workflow, seller reputation only when evidence-backed.
- Operations: role-gated moderation and business administration with audit logs.
- Resilience: offline drafts, retryable synchronization, conflict handling, image upload recovery, and low-bandwidth caching.

## 6. Technical and governance constraints
- PostgreSQL remains the authoritative shared store; SQLite remains local/offline only.
- Reuse existing business-profile, membership, role, moderation, and audit models where their semantics fit; do not create parallel identity or business records.
- Any schema change requires an additive Alembic migration, downgrade/recovery consideration, and migration tests.
- Use existing S3-compatible object storage for media; never store binary image data in database rows or expose private storage keys.
- Amharic is primary and English secondary. Do not add Maale translations.
- CI uses synthetic data only. No production data or secrets in tests.
- Preserve the successful CI baseline and current feature branch. Keep PR #1 draft and unmerged.
- No merge, production migration, deployment, paid-service commitment, payment activation, or commercial launch is authorized by this addendum.
