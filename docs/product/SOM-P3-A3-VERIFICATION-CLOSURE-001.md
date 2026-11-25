# South Omo Market — P3 A3.1/A3.2 Verification Closure

- **Record ID:** SOM-P3-A3-VER-CLOSE-001
- **Version:** 1.0
- **Status:** VERIFIED-CLOSED (A3.1 and A3.2 only)
- **Repository:** `akefadaka-git/south-omo-market`
- **Branch:** `feat/customer-platform-foundation`
- **Verified implementation commit:** `3ba78adeb54f9be3bc843901f2aaa6e34beaaa41`
- **Workflow:** [GitHub Actions run #45568219124](https://github.com/akefadaka-git/south-omo-market/actions/runs/45568219124)
- **Verification date:** 2026-11-26

## 1. Closure scope

This record closes verification of the already-authorized P3 A3.1 and A3.2 implementation at the commit above. It does not close P3 as a whole and does not approve merge, deployment, release APK publication, or application of migrations to any shared or production database.

## 2. A3.1 — Verified business authorization

**Result: PASS**

The implementation enforces listing access against the seller's business profile, active and unexpired business membership, permitted membership role, active user, active business, and verified business status. Listing create/update/submit/image operations use the server-side gate. Public listing visibility excludes businesses that are inactive or unverified and checks active authorized membership. Seller profile creation no longer grants a global merchant role as a substitute for business authorization. Administrative listing approval rechecks business verification and active membership.

Regression coverage includes revocation of business verification before administrative approval and denial for expired membership.

## 3. A3.2 — Inquiry contact-disclosure consent

**Result: PASS**

Inquiry creation requires an explicit contact-disclosure consent value. Without consent, the stored inquiry uses a generic buyer identity and does not retain or expose the buyer's contact value; the seller inbox also suppresses buyer identity/contact details. With consent, the contact value and consent timestamp are recorded and the authorized seller inbox may display the permitted details.

Migration `0020_seller_contact_consent` adds the consent fields and consistency constraint, scrubs historical inquiry contact details, and has a corrected downgrade order that removes the constraint before restoring nullable legacy values.

## 4. CI evidence

Workflow run #45568219124 completed all jobs. Required verification jobs passed:

| Job | Result |
|---|---|
| Backend | PASS |
| Mobile (Flutter analyze and tests) | PASS |
| Admin (dependency audit, build, tests) | PASS |
| Android staging test APK | PASS |
| Android release APK | SKIPPED — release API URL is not configured |

The release job is an optional/configuration-gated job; its skip does not indicate a staging build failure. The required jobs all succeeded, so the workflow's effective conclusion is **SUCCESS**.

### Backend and migration evidence

- Ruff: `All checks passed!`
- Backend pytest: **82 passed, 23 warnings, 0 failures**.
- PostgreSQL full migration-chain and append-only audit-trigger integration: **2 passed, 4 warnings**.
- S3-compatible storage integration: **3 passed**.
- The PostgreSQL migration integration step completed successfully against the CI test database. This is CI verification only; no shared or production database was migrated.

### Android staging artifact

- Artifact: `south-omo-market-android-staging-test-apk`
- Artifact ID: `15001850156`
- Contents: 3 debug APK files
- Size: 123,820,695 bytes
- SHA-256: `17b99be5ec94e2f5d4f8b8720385b43257874edd2b913de4f195086c87386c59`
- [Download artifact from GitHub Actions](https://github.com/akefadaka-git/south-omo-market/actions/runs/45568219124/artifacts/15001850156)
- Artifact retention expiry reported by GitHub: 2026-12-09.

## 5. Files and migration covered

Implementation and test evidence at the verified commit includes:

- `backend/app/governance.py`
- `backend/app/routers/listings.py`
- `backend/app/routers/inquiries.py`
- `backend/app/routers/sellers.py`
- `backend/app/routers/admin.py`
- `backend/app/models.py`
- `backend/app/governance_models.py`
- `backend/migrations/versions/0020_seller_business_contact_consent.py`
- `backend/tests/test_seller_security_consent.py`
- `backend/tests/test_commerce_migrations.py`

The migration head asserted by the commerce migration test is `0020_seller_contact_consent`.

## 6. Boundaries and remaining work

- A3.1 and A3.2: **VERIFIED-CLOSED** at commit `3ba78adeb54f9be3bc843901f2aaa6e34beaaa41`.
- A3.3 onward: **NOT CLOSED**; subsequent P3 implementation and regression work remain.
- Full P3 A3: **IN PROGRESS**.
- A4: **NOT STARTED**.
- A5 deployment: **NOT AUTHORIZED / NOT STARTED**.
- No PR merge, deployment, release APK publication, or shared/production database migration was performed.
- PR #1 remains separate and open/draft/unmerged.

## 7. Next authorized implementation stage

Proceed to A3.3: implement versioned listing edits and material-change moderation while preserving the approved A1 policy: material edits require administrator review; the last approved version remains public while a material edit is pending unless a safety/compliance concern requires suspension; rejected edits must not overwrite the approved version; minor corrections may publish directly with an audit record. Preserve unrelated work and continue on the existing branch.
