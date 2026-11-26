# South Omo Market — P3 A3.3 Verification Closure

- **Record ID:** SOM-P3-A3.3-VER-CLOSE-001
- **Version:** 1.0
- **Status:** VERIFIED-CLOSED — A3.3 scope only
- **Repository:** `akefadaka-git/south-omo-market`
- **Branch:** `feat/customer-platform-foundation`
- **Verified implementation/test commit:** `596ecaa4508da130b60d3348ab0e7b558c8d5405`
- **Implementation evidence record:** [SOM-P3-A3.3-IMPLEMENTATION-001.md](SOM-P3-A3.3-IMPLEMENTATION-001.md)
- **CI run:** [GitHub Actions #45820413019](https://github.com/akefadaka-git/south-omo-market/actions/runs/45820413019)
- **Verification date:** 2026-11-26

## 1. Closure scope

This record closes A3.3 — versioned listing edits and material-change moderation — against the approved P3 scope. It does not close all of A3, P3, or the product. It does not authorize merge, deployment, production release, shared database migration, or commercial activation.

## 2. Acceptance results

| Acceptance area | Result | Evidence |
|---|---|---|
| Published listing material edits are versioned and held for moderation | PASS | Existing pending-edit and public-visibility regression tests |
| Existing published version remains visible while material edit is pending | PASS | Existing public visibility and pending edit tests |
| Duplicate pending edits are rejected | PASS | Existing commerce API regression test |
| Admin queue exposes pending edit | PASS | New authenticated API route test |
| Admin approval applies valid proposed values and audits | PASS | Existing approval-handler regression test |
| Admin rejection preserves published values and audits | PASS | New decision-route regression test |
| Minor description correction publishes directly and audits | PASS | New API PATCH route test |
| Business verification revoked after submission blocks approval | PASS | New isolated parameterized API route case; HTTP 409 |
| Seller membership revoked after submission blocks approval | PASS | New independently reset parameterized API route case; HTTP 409 |
| Failed approval leaves published listing unchanged and edit pending | PASS | Both revocation cases |
| Migration chain including `0021_listing_edit_versions` | PASS — CI database only | PostgreSQL migration integration |
| Backend, admin, mobile and Android staging CI | PASS | Workflow #45820413019 |

## 3. Regression test details

Four new test cases were added in commit `596ecaa4508da130b60d3348ab0e7b558c8d5405`:

- `test_minor_description_correction_is_published_through_authenticated_api`
- `test_admin_edit_queue_and_approval_fail_closed_after_authority_revocation[business-verification-revoked]`
- `test_admin_edit_queue_and_approval_fail_closed_after_authority_revocation[seller-membership-revoked]`
- `test_admin_edit_rejection_route_preserves_published_values_and_records_audit`

The two revocation cases each reset the synthetic business to verified/active and its owner membership to active before submitting the edit. Each then applies only its own revocation, proving the business-verification and membership failure paths independently.

**Test-boundary qualification:** The commerce API tests use fixture dependency overrides to isolate the moderation routes; seller authorization functions are stubbed in the relevant cases and the admin dependency is overridden for admin requests. They verify moderation route behavior and fail-closed state transitions, not production authentication-provider or full RBAC integration. The seller/business authorization foundation was separately verified under A3.1. Broader integrated/system-level verification remains A4 work.

## 4. CI evidence

Workflow #45820413019 (run number 1118, attempt 1) completed with overall conclusion **SUCCESS** on the verified code/test commit:

`596ecaa4508da130b60d3348ab0e7b558c8d5405`

- Backend Ruff: PASS.
- Backend pytest: **98 passed, 23 warnings, 0 failures**.
- PostgreSQL migration and append-only audit-trigger integration: **2 passed, 4 warnings**.
- S3-compatible storage integration: **3 passed**.
- Admin dependency audit, build and tests: PASS.
- Flutter analysis and tests: PASS.
- Android staging readiness, universal debug APK build and artifact upload: PASS.
- Android release APK: SKIPPED because release API URL is not configured; this is an expected release configuration gate.

No CI failure was reported. The warnings are recorded rather than treated as test failures.

## 5. Android staging artifact

- Artifact: `south-omo-market-android-staging-universal-apk`.
- Artifact ID: `15118356711`.
- [GitHub Actions artifact](https://github.com/akefadaka-git/south-omo-market/actions/runs/45820413019/artifacts/15118356711).
- ZIP size: 70,993,828 bytes.
- ZIP digest: `sha256:c29a48c7ff42e99cfbc9831d477d1a2607b33f97754ade6e760530ff015d3bef` (independently matched after download).
- Contains one `app-debug.apk` (146,514,575 bytes).
- Extracted APK SHA-256: `264a6b141b90030814a7d7007649175d35d5598b9b20f74cb1703311a9b22c40`.

This is a staging/debug APK. It is not a signed production release and no physical-device installation test is claimed.

## 6. Migration, change and release boundaries

- Migration `0021_listing_edit_versions` passed against the ephemeral CI PostgreSQL database.
- No shared, staging, or production database migration was performed.
- No PR was merged; PR #1 remains open/draft/unmerged.
- No deployment, release publication, production configuration change, or commercial activation occurred.
- No changes were made to `main`.

## 7. Stage status after A3.3

- A3.1: VERIFIED-CLOSED.
- A3.2: VERIFIED-CLOSED.
- A3.3: VERIFIED-CLOSED by this record.
- A3.4 onward: NOT YET VERIFIED / NOT CLOSED.
- A3 overall: IN PROGRESS.
- A4: NOT STARTED.
- A5: NOT AUTHORIZED / NOT STARTED.

## 8. Next stage

Continue only with the next already-approved A3 work item on the existing branch, preserving unrelated work and the approved P3 scope. Keep A4 verification and A5 deployment separate. No merge or production-impacting action is authorized by this closure.
