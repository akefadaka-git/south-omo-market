# A3.3 — Versioned Listing Edits and Material-Change Moderation

**Record:** SOM-P3-A3.3-001  
**Status:** VERIFIED-CLOSED — A3.3 implementation and scoped verification complete  
**Branch:** `feat/customer-platform-foundation`  
**Implementation and verification commit:** `596ecaa4508da130b60d3348ab0e7b558c8d5405`  
**CI:** [Workflow run #45820413019](https://github.com/akefadaka-git/south-omo-market/actions/runs/45820413019) — SUCCESS

## Behavior delivered

- Draft listings retain the existing direct-edit workflow.
- Published listing edits are stored as proposed values in a separate `listing_edits` record; the public listing remains unchanged while review is pending.
- Only description formatting changes that preserve the exact Unicode word-token sequence (case, whitespace, and punctuation normalization) publish directly. These are audit-logged. Wording, claims, prices, identity, category, attributes, and location changes require moderation.
- A database uniqueness constraint permits at most one pending edit per listing, including concurrent submissions.
- Admins receive a dedicated pending edit queue and approve/reject endpoint. Approval rechecks active verified business and seller membership, plus active category/location references and proposed category/attribute validity.
- Rejection leaves the currently published listing unchanged.
- Every approval, rejection, and direct minor correction creates an audit event.
- A location-ID-only proposed edit also derives the corresponding location label when the caller omits it.

## Latest CI evidence

- Run ID: `45820413019`; run number: **1118**; attempt: **1**.
- Head branch: `feat/customer-platform-foundation`.
- Head SHA: `596ecaa4508da130b60d3348ab0e7b558c8d5405`.
- Started: 2026-11-26 12:31:16 UTC; completed: 2026-11-26 12:37:10 UTC.
- Overall workflow conclusion: **SUCCESS**.

| Job / check | Result |
|---|---|
| Backend Ruff | PASS |
| Backend pytest | **98 passed, 23 warnings, 0 failures** |
| PostgreSQL migration and append-only audit-trigger integration | **2 passed, 4 warnings** |
| S3-compatible storage integration | **3 passed** |
| Admin dependency audit, build and tests | PASS |
| Flutter analysis and tests | PASS |
| Android staging readiness, universal debug APK build and upload | PASS |
| Android production release APK | SKIPPED — release API URL not configured; expected configuration gate |

The backend job log confirms the exact pytest and integration counts. The PostgreSQL test used the CI service database only. No shared, staging, or production database migration was applied.

## A3.3 route and regression coverage

The four new test cases introduced in `backend/tests/test_commerce_api.py` passed in the 98-test backend suite:

1. `test_minor_description_correction_is_published_through_authenticated_api` — API PATCH path, minor-correction response, published description and audit event.
2. `test_admin_edit_queue_and_approval_fail_closed_after_authority_revocation[business-verification-revoked]` — queue route, post-submission business verification revocation, approval returns 409, published listing unchanged, edit remains pending.
3. `test_admin_edit_queue_and_approval_fail_closed_after_authority_revocation[seller-membership-revoked]` — independently resets the synthetic business and membership before the case, then verifies membership revocation after submission causes approval to return 409 without changing the published listing.
4. `test_admin_edit_rejection_route_preserves_published_values_and_records_audit` — queue and decision routes, rejection response, published values preserved, rejection audit event recorded.

Existing regression tests also cover successful approval application and audit logging, pending edit visibility, duplicate pending-edit rejection, and location label derivation.

**Test-boundary note:** These route tests use the commerce API fixture and test dependency overrides to isolate moderation behavior. Seller authorization dependencies are stubbed in the relevant route tests and the admin dependency is overridden for the admin cases; this is not a production identity-provider or full RBAC end-to-end test. The underlying seller/business authorization controls were separately verified and closed in A3.1. A4 remains responsible for broader integrated/system-level verification.

## Staging artifact

- Artifact name: `south-omo-market-android-staging-universal-apk`.
- Artifact ID: `15118356711`.
- [Download from GitHub Actions](https://github.com/akefadaka-git/south-omo-market/actions/runs/45820413019/artifacts/15118356711).
- ZIP size: **70,993,828 bytes**.
- GitHub artifact digest: `sha256:c29a48c7ff42e99cfbc9831d477d1a2607b33f97754ade6e760530ff015d3bef`.
- Downloaded ZIP digest independently matched GitHub's digest.
- ZIP contains one `app-debug.apk`, size **146,514,575 bytes**.
- Extracted APK SHA-256: `264a6b141b90030814a7d7007649175d35d5598b9b20f74cb1703311a9b22c40`.
- The GitHub Actions artifact link above is the durable repository-hosted download reference; the extracted APK checksum is recorded for integrity verification.

This is a staging/debug APK, not a signed production release. No physical-device installation test is claimed.

## Migration and scope boundaries

- Migration `0021_listing_edit_versions` passed the PostgreSQL CI migration-chain integration check.
- No shared, staging, or production database was migrated.
- No merge, deployment, release publication, commercial activation, or production configuration change was performed.
- PR #1 remains separate and unmerged.
- A3.1 and A3.2 remain VERIFIED-CLOSED under their existing closure record.
- A3.3 is VERIFIED-CLOSED for its approved implementation scope.
- A3.4 onward remains subject to its own implementation and evidence.
- A4 is NOT STARTED.
- A5 is NOT AUTHORIZED / NOT STARTED.

## Closure basis

A3.3 acceptance gaps recorded in the earlier version of this document are addressed by the four passing route-level test cases above and the complete successful CI run. The successful approval business logic, rejection behavior, pending visibility, duplicate prevention, and audit behavior are covered by the existing regression suite. Closure is limited to A3.3; it does not imply full platform readiness or waive A4/A5 stage gates.
