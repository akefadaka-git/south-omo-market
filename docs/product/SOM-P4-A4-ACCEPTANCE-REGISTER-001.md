# A4 Acceptance Register and Synthetic Migration-Test Evidence — South Omo Market

**Date:** 2026-11-26  
**Repository:** `akefadaka-git/south-omo-market`  
**Working branch:** `feat/customer-platform-foundation`  
**Frozen A2 main:** `1e0dc04d66b0b80b29ce81b28084c1d8211ce708`  
**A3.4 verified-closed application baseline:** `6221e790f2faf4fcd61b1950d8950c4a26002716`  
**A3.4 CI evidence:** run #1129 / `45830363627` — https://github.com/akefadaka-git/south-omo-market/actions/runs/45830363627

## Governance and scope

This register starts A4 acceptance tracking without reopening A3.4. It does not authorize merge, production migration, deployment, production signing, paid services, personal-data processing, or commercial operation. The frozen A2 main branch remains untouched.

A4 acceptance is evidence-led. Automated tests, a staging readiness response, or a successful APK build are not substitutes for physical-device, accessibility, end-to-end, field, or independent security acceptance.

## Isolated synthetic-only migration target — VERIFIED

**Selected target:** GitHub Actions job-local PostgreSQL 16 service container, created fresh for the CI job and destroyed at job teardown. This is preferred over a Neon branch for this test because it is isolated, ephemeral, no-cost within the existing CI route, and does not clone production data.

**Isolation evidence:**
- Workflow: `.github/workflows/ci.yml`; backend job provisions a PostgreSQL 16 service container and points `TEST_POSTGRES_URL` only to `localhost:5432/south_omo_market`.
- The PostgreSQL container log in run #1129 shows a fresh `initdb`, creation of the test database, and successful shutdown/removal of the service container at job completion.
- No Neon connection string or shared Neon branch is used by this migration test.
- Integration fixtures use synthetic identities and deterministic market/location reference data. No production database snapshot, customer records, seller PII, or live service credentials are copied into the test target.

**Migration-chain evidence:**
- `backend/tests/test_postgres_integration.py::test_postgresql_full_migration_chain_and_append_only_audit_trigger` runs Alembic `upgrade head` from the empty service database.
- It verifies the expected schema, final Alembic revision `0021_listing_edit_versions`, seeded reference rows, and append-only audit trigger behavior.
- It then runs Alembic `downgrade base` and verifies that the application tables and audit trigger are removed.
- Run #1129 backend job completed successfully; PostgreSQL integration suite: **2 passed**. Job log confirms the migration test and the teardown of the PostgreSQL service container.
- Run URL: https://github.com/akefadaka-git/south-omo-market/actions/runs/45830363627

**Disposition:** PASS — isolated synthetic-only migration chain verified on application SHA `6221e790f2faf4fcd61b1950d8950c4a26002716`. This satisfies the migration-test isolation objective. A separate Neon branch migration was deliberately NOT RUN and is not required for this acceptance evidence. The Neon project's Singapore region remains unsuitable for Ethiopia-residency claims or personal data.

## A4 acceptance matrix

| Workstream | Required evidence | Current status | Boundary / next action |
|---|---|---|---|
| Physical Android device | Install the exact staging APK on named handset(s); record Android version, model, build SHA, install/upgrade, permissions, camera/gallery, offline/reconnect, crashes and screenshots/logs | NOT RUN | Requires hands-on device session; CI APK build is not device acceptance |
| Accessibility | TalkBack screen-reader traversal, semantic labels/order, focus behavior, 200% text scaling, contrast, touch targets, keyboard/external input where applicable, Amharic/English layout and error announcements | NOT RUN | Requires device-level test session and recorded results |
| End-to-end system | Buyer discovery → listing detail → inquiry; seller sign-in/profile → draft/create/edit → submit; admin review/moderation/report resolution; offline queue/retry; API/database/media behavior; role isolation | PARTIAL | Existing component/API/database regression suites and staging `/ready` pass; no complete cross-role staging acceptance run is evidenced |
| Field acceptance | With consent, review real market/category vocabulary, product coverage, market-day schedule correctness, low-bandwidth/offline behavior and user comprehension with South Omo participants | NOT RUN | Requires field participants and Owner-approved pilot protocol; do not collect unnecessary personal data |
| Independent security acceptance | Independent reviewer not involved in implementation; review threat model, authn/authz and tenant boundaries, IDOR, rate limiting, uploads/evidence handling, malware/content validation, audit immutability, session/token lifecycle, abuse paths, secrets/dependencies and remediation retest | NOT RUN | Reviewer and scope must be independent; do not label internal regression tests an independent review |
| Privacy/legal/data controls | Ethiopia data-residency evidence for DB/object storage/logs/backups; lawful basis, notices, retention/deletion, DPIA, processor/DPO applicability, incident response and Ethiopian legal review | BLOCKED / NOT ACCEPTED | Existing Neon region is Singapore; no personal data may be placed there for this project |
| Operational media recovery | Ethiopia-located persistent storage decision, backup evidence and successful restore drill using synthetic data | BLOCKED / NOT RUN | No approved Ethiopia-located no-cost provider, production bucket or credentials evidenced |
| Phone ownership verification | Real handset delivery and verified OTP using an approved durable no-cost provider | BLOCKED | No simulation or false verified status; no paid service without separate authorization |

## Existing automated evidence — not A4 closure

Run #1129 is successful on the A3.4 application-code SHA. The backend job passed 98 backend tests, 2 PostgreSQL integration tests and 3 S3-compatible integration tests; admin passed 4 tests/build/audit; Flutter passed 44 tests and analysis; Android staging APK build and staging readiness checks passed. The production release job was skipped by its gate.

These are reusable baseline evidence only. They do not prove live staging business journeys, physical-device behavior, field suitability, accessibility conformance, independent security assurance, legal compliance, or production readiness.

## A4 acceptance recording rules

For each execution, record:
- test case ID and requirement;
- tester identity/role (or independent reviewer organization);
- date/time and environment;
- app/API commit SHA and APK hash where applicable;
- device model, OS and assistive-technology settings where applicable;
- synthetic or consented test-data classification;
- expected result, actual result, PASS/FAIL/BLOCKED/NOT RUN;
- evidence reference and defect/remediation link;
- retest result and acceptance sign-off.

No real personal data is to be entered into the synthetic CI database. Any field research must use an approved consent and data-minimization protocol.

## Stage status

- A1: VERIFIED-CLOSED.
- A2: VERIFIED-CLOSED at frozen main SHA `1e0dc04d66b0b80b29ce81b28084c1d8211ce708`.
- A3.4: VERIFIED-CLOSED; preserve exact baseline and run #1129 evidence.
- Synthetic-only migration chain: VERIFIED for CI job-local PostgreSQL 16 on SHA `6221e790f2faf4fcd61b1950d8950c4a26002716`.
- A3 overall: OPEN pending its own Owner disposition/closure record; this A4 register does not close A3.
- A4: IN PROGRESS — acceptance evidence matrix established; physical-device, accessibility, full end-to-end, field, and independent security acceptance remain NOT ACCEPTED.
- A5: NOT AUTHORIZED / NOT STARTED.
- Merge, main modification, production migration, production signing, deployment, payments, paid providers, and commercial activation: NOT AUTHORIZED.
