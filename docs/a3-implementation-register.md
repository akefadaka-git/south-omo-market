# A3 implementation register — South Omo Market

## Latest exact-head automated verification

- Current corrective feature head: `03382c8ab61510f71bf50fc9aa3b0d726e7795f4`.
- Exact-head CI for this corrective head: NOT YET RECORDED; workflow run/status lookup returned no run/status at report update time.
- Last verified predecessor: `7e4494c207d7e3cab452ba60dfb060d8baa6d64a`, GitHub Actions run #805 — PASS: https://github.com/akefadaka-git/south-omo-market/actions/runs/45154338290.
- Predecessor run #805: backend Ruff passed; 37 backend tests passed; PostgreSQL migration/audit integration 1 passed; S3 integration 3 passed; admin build passed with 3 Vitest tests and zero reported dependency vulnerabilities; Flutter analysis passed with 34 tests. Android release APK remained SKIPPED because no production API URL was configured.
- The corrective commits after that predecessor are not covered by run #805. Do not treat predecessor evidence as verification of the current head.
- Overall A4 remains PARTIAL / NOT VERIFIED pending exact-head CI and the operational acceptance gates listed below.

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
| Discovery pagination | Mobile limit/offset; duplicate-safe page append with independent fetched-row offset; empty-page termination; retry and filter-reset boundary regressions | IMPLEMENTED; widget tests passed at run #797 |
| Seller identity and listing lifecycle | Registration/login, seller profile, draft, submit-for-review, moderation | IMPLEMENTED |
| Seller inquiry workflow | Buyer inquiry and seller inbox/status handling | IMPLEMENTED |
| Offline seller drafts | SQLite local drafts and retryable synchronization | IMPLEMENTED |
| Listing media | Validated image decode/re-encode, ownership checks, idempotent client image IDs, provider-neutral storage adapter; no-cost Ethiopia-hosted object storage and recoverable backups remain unavailable under current constraints | IMPLEMENTED; production persistence BLOCKED |
| Moderation and audit | Admin-only listing decisions and append-only audit event protection | IMPLEMENTED |
| Reports and complaints | Authenticated listing/seller reports, bounded evidence summaries/references, reporter status view, admin pending/in-review queue, investigation/resolve/dismiss decisions, listing removal, reversible listing removal/restoration, seller account suspension/reinstatement, permanent pre-suspension token revocation, public hiding of suspended sellers' listings/media and append-only audit events; API, mobile and admin UI slices added | IMPLEMENTED; backend and mobile regression suites pass at exact head `53607b25c695b7e4bc27f9a4a028ee012e53fbed` (run #797) |
| Backend health/readiness | Liveness and database readiness endpoints | IMPLEMENTED |
| Manual CI entry point | `workflow_dispatch` added alongside push and pull-request triggers; invalid YAML shell message corrected | IMPLEMENTED; exact-head run #797 passed at `53607b25c695b7e4bc27f9a4a028ee012e53fbed`; YAML pre-job defect fixed |
| Search/sort regression coverage | Synthetic API test for description search, price ordering and invalid sort rejection | VERIFIED; backend/mobile tests passed at run #797 |
| Category hierarchy data model | Self-referencing category parent, original seed plus additive migration `0007_catalogue_expansion` with 24 additional leaves across all seven top-level groups; root/child API and leaf-category enforcement | VERIFIED; PostgreSQL migration-chain test passed at run #797; isolated Neon branch migration remains separate |
| Category-specific listing attributes | Expanded typed schemas across livestock, agriculture, food, retail, services, rentals and jobs; API validates required fields, text limits, numeric ranges, finite numbers, booleans, choices, unknown keys and malformed schema; create/update/offline-sync enforcement | VERIFIED; backend and Flutter regression tests passed at run #797 |
| Grouped mobile category browser | Removed hard-coded topic chips; renders API root categories and actual leaf subcategories | VERIFIED; Flutter suite passed at run #797 |
| Category-driven seller creation/editor | API-loaded leaf categories; schema-driven text, number, choice and boolean controls; required/range/length/choice validation; field-level feedback; edit PATCH persists attributes | VERIFIED; Flutter test suite passed at run #797 (31 tests) |
| Offline category-specific drafts | SQLite v4 `attributes_json` and category-catalogue cache migrations; schema validation runs before local save; category-specific JSON is persisted/restored offline and included in sync payload | IMPLEMENTED; backend and Flutter regression tests passed at run #797 |

## Explicitly unresolved A3 scope

These items must not be marked complete without implementation and evidence:

1. **Catalogue depth:** additive migration `0007_catalogue_expansion` adds 24 leaf categories and schemas beyond the initial seeds; the PostgreSQL migration chain and backend/mobile regression suites pass in run #797. Still open: apply only to the isolated Neon testing branch when separately authorized, field-pilot catalogue review and any scope adjustments approved from that review.
2. **Pagination boundary tests:** duplicate IDs across pages, empty final page, initial-load retry and sort/filter reset regressions passed in the 31-test Flutter suite at run #797.
3. **Maale localization:** human-reviewed translations, terminology register, script/font validation and Maale-speaking approval. Empty strings are not translations and must not be presented as such.
4. **Seller phone ownership:** no provider is integrated. SMSHub advertises 10 one-time free credits after identity/KYC approval, but its standard service is prepaid (Ethio Telecom 1 credit, Safaricom 2); this is a limited pilot allowance, not a durable no-cost service. Africa's Talking sandbox does not deliver to real handsets. Do not configure or use a paid path, simulate OTP, or imply a phone number is verified. Reassess only if a genuinely no-cost live-delivery agreement is available.
5. **Private intelligence integration:** no approved service contract, credentials or provider SDK is available. Keep the marketplace functional without it; do not invent an integration.
6. **Operational media persistence:** provider-neutral S3 adapter and encrypted backup/restore inventory tooling exist, but no Ethiopia-located no-cost persistent object-storage provider has been verified. Cloudflare R2 is technically compatible and has a free tier but is not approved for local personal data because its published locations do not include Ethiopia. Article 22(1) data residency blocks production use until Ethiopia-located database, object storage, logs and backups are selected and tested. No bucket, secrets or restore drill exists.
7. **Accessibility and localization acceptance:** complete screen-by-screen Amharic review, text scaling, semantics, contrast, keyboard/screen-reader checks and physical-device validation. Maale translations remain unprovided and require native-speaker review; no translations are fabricated.
8. **Security and privacy acceptance:** report workflow baseline is implemented; independent review, evidence-attachment security, abuse escalation, retention/deletion and Ethiopian legal review remain open. A new compliance register records Article 22(1) data-residency as a production blocker; current Singapore-hosted test services must remain synthetic-only. DPIA, DPO/processor analysis, privacy notice, processing records and 72-hour breach response remain unimplemented.
9. **Release signing:** CI's ephemeral signing key is for test artifacts only. Added an owner-local JKS generator, Gradle signing configurator requiring an owner-approved permanent application ID, and manually dispatched/tag-gated App Bundle workflow. No production key, GitHub secrets, protected signing environment, API URL or signed production artifact exists.
10. **Production privacy gates:** API startup now fails closed unless Ethiopia data residency evidence, legal review, HTTPS privacy notice, DPIA, processing records, DPO applicability assessment (and contact if required) and verified seller-phone controls are explicitly attested. These settings are release gates, not proof that the evidence exists. Current settings remain false/unknown.

## Verification gates

- Backend, PostgreSQL, S3, admin and Flutter suites have all passed on the exact current head in run #797. The earlier zero-job workflow failure was caused by an invalid YAML plain scalar containing `: `; it was fixed with a block scalar. CI now creates named jobs correctly.
- Verify Alembic migration chain against an isolated Neon testing branch; do not run migrations against a production database.
- Verify live `/health`, `/ready`, and public discovery endpoints only after a real HTTPS staging URL exists.
- Install and exercise the resulting APK on a physical Android device. CI build success alone is not device acceptance.
- Exact verification URL and SHA are recorded above. The generated admin dependency lockfile is retained as a CI artifact for review: https://github.com/akefadaka-git/south-omo-market/actions/runs/44921104886/artifacts/14714055802. It is not yet committed as `admin/package-lock.json`.

## Governance

- A1 and A2 remain VERIFIED-CLOSED.
- This A3 register remains OPEN until every required A3 item is either implemented and verified or explicitly removed from A3 scope by an owner-approved decision.
- A4 verification remains separate from A3 implementation.
- A5 deployment, PR merge, production data activation and commercial launch require separate authorization.
- No paid plan, card, top-up or billing activation is part of this work.


## Maale Market Directory and Weekly Schedule — A3 corrective pass implemented; exact-head verification pending

- Target branch: `feat/a3-platform-foundation`; do not create a new branch or modify `main`.
- Adds a dedicated `markets` and `market_schedule_days` schema, with nullable verified geographic association, optional market descriptions, optional effective date ranges, and an eight-record owner-provided initial seed.
- Public weekly schedule, weekday, bounded name/code/description search and weekday-filter APIs; administrator-only market CRUD, schedule editing, effective-date editing, activation/deactivation and bounded audit-history retrieval; existing `require_admin` and append-only audit events are reused.
- React administration includes directory management, search and weekday filters, descriptions, optional existing-location selection, effective-date-aware day editor, audit-history view and weekly overview.
- Flutter includes a searchable seven-day market calendar with weekday filtering and a separate read-only SQLite schedule cache with offline fallback and last-updated display.
- Synthetic backend tests cover market search, date-window behavior, invalid date ranges and administrator audit retrieval. Migration tests assert all eight exact market/day mappings, new schema columns and a downgrade/re-upgrade seed cycle. Admin build/tests and Flutter analysis/tests still require exact-current-head CI.
- No production migration, merge, deployment, commercial activation or paid service is authorized.
