# A3.3 — Versioned Listing Edits and Material-Change Moderation

**Record:** SOM-P3-A3.3-001  
**Status:** IMPLEMENTED — CI VERIFIED; targeted route-level verification remains before A3.3 VERIFIED-CLOSED  
**Branch:** `feat/customer-platform-foundation`  
**Verification head:** `bc8c3e3811787ea4be9999bb04ec702941a4cfa8`

## Behavior

- Draft listings retain the existing direct-edit workflow.
- Published listing edits are stored as proposed values in a separate `listing_edits` record; the public listing remains unchanged while review is pending.
- Only description formatting changes that preserve the exact Unicode word-token sequence (case, whitespace, and punctuation normalization) publish directly. These are audit-logged. Wording, claims, prices, identity, category, attributes, and location changes require moderation.
- A database uniqueness constraint permits at most one pending edit per listing, including concurrent submissions.
- Admins receive a dedicated pending edit queue and approve/reject endpoint. Approval rechecks active verified business and seller membership, plus active category/location references and proposed category/attribute validity. Rejection leaves the currently published listing unchanged.
- Every approval, rejection, and direct minor correction creates an audit event.
- A location-ID-only proposed edit also derives the corresponding location label when the caller omits it.

## Verification evidence

### GitHub Actions

- Workflow: [CI run #45754206229](https://github.com/akefadaka-git/south-omo-market/actions/runs/45754206229) — **SUCCESS**, attempt 1.
- Branch: `feat/customer-platform-foundation`.
- Workflow head and verified branch head: `bc8c3e3811787ea4be9999bb04ec702941a4cfa8`.
- Run completed 2026-11-26 04:21:55 UTC.
- Backend job `139688878143`: SUCCESS — Ruff passed; pytest **94 passed**; PostgreSQL migration/audit-trigger integration **2 passed**; S3-compatible object-storage integration **3 passed**.
- Mobile job `139688878270`: SUCCESS — `flutter analyze --no-fatal-infos` and `flutter test` passed.
- Admin job `139688878054`: SUCCESS — dependency audit, `npm run build`, and `npm test` passed.
- Android staging job `139688877698`: SUCCESS — HTTPS staging origin validation and live `/ready` check passed (`status=ready`, `database=ok`); Flutter 3.35.7 generated all three split-ABI debug APKs and uploaded them.
- Android release job `139688879500`: SKIPPED because the release API URL is not configured. This is an intentional configuration gate, not a failed job.

### Staging APK artifact

- Artifact: [south-omo-market-android-staging-test-apk](https://github.com/akefadaka-git/south-omo-market/actions/runs/45754206229/artifacts/15087500919)
- Artifact ID: `15087500919`; archive size: **123,820,700 bytes**; retention expiry: **2026-12-10 04:21:45 UTC**.
- GitHub artifact archive digest: `sha256:03b4ad98d9e0f42da102aa46517427b3382d5dc0fc589ffdfb0ea3116b3828cb`.
- The archive was downloaded and inspected; its SHA-256 matched GitHub's published digest and it contains exactly these APK files:
  - `app-armeabi-v7a-debug.apk` — 57,615,849 bytes.
  - `app-arm64-v8a-debug.apk` — 77,912,569 bytes.
  - `app-x86_64-debug.apk` — 64,217,359 bytes.
- The digest above is for the ZIP artifact, not an individual APK. No individual APK checksum or device-install test is asserted here.

### A3.3 regression coverage

- `test_published_listing_material_edit_stays_private_until_admin_rejects`: verifies pending edits do not alter public listing output, duplicate pending submissions are rejected, rejection preserves published price/status, and an audit event is written.
- `test_admin_approval_applies_pending_material_edit_and_audits`: verifies approval applies proposed values, preserves published status, clears the pending key, and writes an audit event.
- `test_location_id_only_edit_updates_location_label`: verifies a location-ID-only proposal receives the matching location label.
- Existing classifier coverage verifies the narrow direct-publish rule for formatting-only description changes.
- The public visibility assertion uses the test client. Seller-update and admin-decision regression cases exercise the handler functions directly with the commerce fixture; they do not constitute full authenticated HTTP end-to-end coverage of every seller/admin route.

### Migration

- Migration `0021_listing_edit_versions` is present in the branch and passed the PostgreSQL CI migration-chain integration test. No shared, staging, or production database migration was applied as part of this work.

## Remaining verification before A3.3 closure

- Add/confirm authenticated route-level coverage for the minor-correction direct-publish path and the admin pending-edit queue/decision routes.
- Add an A3.3-specific fail-closed approval regression for business verification or seller membership being revoked after edit submission but before approval.
- Then record the resulting verification evidence and explicitly close A3.3. The successful workflow and artifact do not, by themselves, close these remaining acceptance gaps.

## Scope boundaries

No chat, payments, delivery, subscriptions, paid promotion, analytics expansion, deployment, merge, release APK publication, or shared database migration is included. Migration is CI-tested only. PR #1 remains unmerged; A4 and A5 remain separate stages.
