# A3 implementation register — South Omo Market

**Branch:** `feat/a3-platform-foundation`  
**Baseline:** frozen A2 `main` at `1e0dc04d66b0b80b29ce81b28084c1d8211ce708`  
**Purpose:** evidence-based implementation register. This file is not an A3 closure certificate.

## Implemented on the feature branch

| Capability | Evidence / scope | State |
|---|---|---|
| Amharic-first Flutter application shell | `mobile/lib/app/market_app.dart`, shared design system, locale-aware strings | IMPLEMENTED |
| English secondary locale | Explicit in-app selection and widget coverage | IMPLEMENTED |
| Public marketplace discovery | Published listings, category/location filters, listing details | IMPLEMENTED |
| Public discovery search | API searches title, description and location; bounded query length | IMPLEMENTED |
| Discovery sorting | Stable newest, price ascending and price descending ordering | IMPLEMENTED |
| Discovery pagination | Mobile limit/offset; duplicate-safe page append with independent fetched-row offset; empty-page termination; retry and filter-reset boundary regressions | IMPLEMENTED; widget tests added, execution pending |
| Seller identity and listing lifecycle | Registration/login, seller profile, draft, submit-for-review, moderation | IMPLEMENTED |
| Seller inquiry workflow | Buyer inquiry and seller inbox/status handling | IMPLEMENTED |
| Offline seller drafts | SQLite local drafts and retryable synchronization | IMPLEMENTED |
| Listing media | Validated image decode/re-encode, ownership checks, idempotent client image IDs, provider-neutral storage adapter | IMPLEMENTED |
| Moderation and audit | Admin-only listing decisions and append-only audit event protection | IMPLEMENTED |
| Reports and complaints | Authenticated listing/seller reports, bounded evidence summaries/references, reporter status view, admin pending/in-review queue, investigation/resolve/dismiss decisions, listing removal, seller account suspension/reinstatement and append-only audit events; API, mobile and admin UI slices added | IMPLEMENTED; test execution pending |
| Backend health/readiness | Liveness and database readiness endpoints | IMPLEMENTED |
| Manual CI entry point | `workflow_dispatch` added alongside push and pull-request triggers | IMPLEMENTED; execution still requires GitHub Actions to run |
| Search/sort regression coverage | Synthetic API test for description search, price ordering and invalid sort rejection | ADDED; execution pending |
| Category hierarchy data model | Self-referencing category parent, original seed plus additive migration `0007_catalogue_expansion` with 24 additional leaves across all seven top-level groups; root/child API and leaf-category enforcement | IMPLEMENTED; migration/test execution pending |
| Category-specific listing attributes | Expanded typed schemas across livestock, agriculture, food, retail, services, rentals and jobs; API validates required fields, text limits, numeric ranges, finite numbers, booleans, choices, unknown keys and malformed schema; create/update/offline-sync enforcement | IMPLEMENTED; backend regression coverage added, execution pending |
| Grouped mobile category browser | Removed hard-coded topic chips; renders API root categories and actual leaf subcategories | IMPLEMENTED; Flutter test execution pending |
| Category-driven seller creation/editor | API-loaded leaf categories; schema-driven text, number, choice and boolean controls; required/range/length/choice validation; field-level feedback; edit PATCH persists attributes | IMPLEMENTED; Flutter test execution pending |
| Offline category-specific drafts | SQLite v4 `attributes_json` and category-catalogue cache migrations; schema validation runs before local save; category-specific JSON is persisted/restored offline and included in sync payload | IMPLEMENTED; storage/sync regression tests added; execution pending |

## Explicitly unresolved A3 scope

These items must not be marked complete without implementation and evidence:

1. **Catalogue depth:** additive migration `0007_catalogue_expansion` adds 24 leaf categories and schemas beyond the initial seeds; schemas use the currently supported text, number, choice and boolean field types. Still open: run migration on an isolated test database, execute backend/mobile tests, field-pilot catalogue review and any scope adjustments approved from that review.
2. **Pagination boundary tests:** widget regressions now cover duplicate IDs across pages, empty final page, initial-load retry and sort/filter reset; execute the tests on the exact current head before marking verified.
3. **Maale localization:** human-reviewed translations, terminology register, script/font validation and Maale-speaking approval. Empty strings are not translations and must not be presented as such.
4. **Seller phone ownership:** no provider is integrated. SMSHub advertises 10 one-time free credits after identity/KYC approval, but its standard service is prepaid (Ethio Telecom 1 credit, Safaricom 2); this is a limited pilot allowance, not a durable no-cost service. Africa's Talking sandbox does not deliver to real handsets. Do not configure or use a paid path, simulate OTP, or imply a phone number is verified. Reassess only if a genuinely no-cost live-delivery agreement is available.
5. **Private intelligence integration:** no approved service contract, credentials or provider SDK is available. Keep the marketplace functional without it; do not invent an integration.
6. **Operational media persistence:** provider-neutral S3 adapter and encrypted backup/restore inventory tooling exist, but no Ethiopia-located no-cost persistent object-storage provider has been verified. Cloudflare R2 is technically compatible and has a free tier but is not approved for local personal data because its published locations do not include Ethiopia. Article 22(1) data residency blocks production use until Ethiopia-located database, object storage, logs and backups are selected and tested. No bucket, secrets or restore drill exists.
7. **Accessibility and localization acceptance:** complete screen-by-screen Amharic review, text scaling, semantics, contrast, keyboard/screen-reader checks and physical-device validation. Maale translations remain unprovided and require native-speaker review; no translations are fabricated.
8. **Security and privacy acceptance:** report workflow baseline is implemented; independent review, evidence-attachment security, abuse escalation, retention/deletion and Ethiopian legal review remain open. A new compliance register records Article 22(1) data-residency as a production blocker; current Singapore-hosted test services must remain synthetic-only. DPIA, DPO/processor analysis, privacy notice, processing records and 72-hour breach response remain unimplemented.
9. **Release signing:** CI's ephemeral signing key is for test artifacts only. A production signing identity and owner-controlled recovery are not configured.

## Verification gates

- Run backend lint and tests, including the category hierarchy/attribute regression, PostgreSQL migration integration, S3 adapter tests, admin build/tests, Flutter analysis/tests (including schema-driven seller forms and offline attribute sync) and Android build on the exact current head.
- Verify Alembic migration chain against an isolated Neon testing branch; do not run migrations against a production database.
- Verify live `/health`, `/ready`, and public discovery endpoints only after a real HTTPS staging URL exists.
- Install and exercise the resulting APK on a physical Android device. CI build success alone is not device acceptance.
- Record exact workflow URL, tested SHA, artifact ID and checksum before closing A4.

## Governance

- A1 and A2 remain VERIFIED-CLOSED.
- This A3 register remains OPEN until every required A3 item is either implemented and verified or explicitly removed from A3 scope by an owner-approved decision.
- A4 verification remains separate from A3 implementation.
- A5 deployment, PR merge, production data activation and commercial launch require separate authorization.
- No paid plan, card, top-up or billing activation is part of this work.
