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
| Discovery pagination | Mobile load-more control backed by API limit/offset; page append and has-more detection | IMPLEMENTED; widget regression added, execution pending |
| Seller identity and listing lifecycle | Registration/login, seller profile, draft, submit-for-review, moderation | IMPLEMENTED |
| Seller inquiry workflow | Buyer inquiry and seller inbox/status handling | IMPLEMENTED |
| Offline seller drafts | SQLite local drafts and retryable synchronization | IMPLEMENTED |
| Listing media | Validated image decode/re-encode, ownership checks, idempotent client image IDs, provider-neutral storage adapter | IMPLEMENTED |
| Moderation and audit | Admin-only decisions and append-only audit event protection | IMPLEMENTED |
| Backend health/readiness | Liveness and database readiness endpoints | IMPLEMENTED |
| Manual CI entry point | `workflow_dispatch` added alongside push and pull-request triggers | IMPLEMENTED; execution still requires GitHub Actions to run |
| Search/sort regression coverage | Synthetic API test for description search, price ordering and invalid sort rejection | ADDED; execution pending |

## Explicitly unresolved A3 scope

These items must not be marked complete without implementation and evidence:

1. **Catalogue depth:** governed subcategory hierarchy, grouped browsing and category-specific seller forms/attributes.
2. **Pagination boundary tests:** load-more UI, API limit/offset integration and a widget test for fetching the second page are implemented; execute the test and add boundary coverage for duplicate prevention, empty final page, retry behavior and filter changes.
3. **Maale localization:** human-reviewed translations, terminology register, script/font validation and Maale-speaking approval. Empty strings are not translations and must not be presented as such.
4. **Seller phone ownership:** OTP verification is not implemented because no SMS provider has been selected or integrated. Do not simulate verification or imply a phone number is verified.
5. **Private intelligence integration:** no approved service contract, credentials or provider SDK is available. Keep the marketplace functional without it; do not invent an integration.
6. **Operational media persistence:** local storage is suitable only for disposable staging. Production needs a selected persistent object store, access policy, lifecycle and recovery tests.
7. **Accessibility and localization acceptance:** complete screen-by-screen Amharic review, text scaling, semantics, contrast, keyboard/screen-reader checks and physical-device validation.
8. **Security and privacy acceptance:** independent review, abuse/report workflow completeness, data retention/deletion and applicable legal review.
9. **Release signing:** CI's ephemeral signing key is for test artifacts only. A production signing identity and owner-controlled recovery are not configured.

## Verification gates

- Run backend lint and tests, PostgreSQL migration integration, S3 adapter tests, admin build/tests, Flutter analysis/tests and Android build on the exact current head.
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
