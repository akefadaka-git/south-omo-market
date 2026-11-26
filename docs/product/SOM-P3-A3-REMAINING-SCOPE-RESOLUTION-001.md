# A3 Remaining Scope Resolution Matrix — South Omo Market

**Date:** 2026-11-26  
**Repository:** `akefadaka-git/south-omo-market`  
**Working branch:** `feat/customer-platform-foundation`  
**Frozen baseline:** A2 `main` — `1e0dc04d66b0b80b29ce81b28084c1d8211ce708`  
**A3.4 closed application-code baseline:** `6221e790f2faf4fcd61b1950d8950c4a26002716`  
**A3.4 engineering-verification evidence:** GitHub Actions run #1129, SUCCESS — https://github.com/akefadaka-git/south-omo-market/actions/runs/45830363627

## Purpose and governing rule

This record reconciles every item in the prior A3 implementation register. It does not alter the A3.4 closure record, authorize merge/deployment, or claim A4/A5 acceptance. The frozen A2 `main` branch remains unchanged. All repository work remains on the existing feature branch.

A3 implementation is distinguished from external service procurement, legal/privacy evidence, field-pilot decisions, physical-device testing, and production release controls. A missing external prerequisite is recorded as BLOCKED or DEFERRED; it is never represented as implemented or verified.

## Resolution matrix

| # | Previously unresolved item | Resolution / disposition | Status |
|---|---|---|---|
| 1 | Catalogue depth | The category hierarchy, additive migration `0007_catalogue_expansion`, typed category attributes, root/leaf APIs, leaf enforcement, grouped mobile browser, schema-driven seller forms and offline category attributes are implemented. PostgreSQL migration-chain and backend/mobile regression evidence is recorded in the A3 register. Applying migrations to a separate Neon test branch remains NOT RUN pending explicit environment/branch authorization. Catalogue suitability review and changes based on field feedback are A4 pilot acceptance, not an unverified code claim. | IMPLEMENTED; isolated Neon apply NOT RUN; field review A4 |
| 2 | Pagination boundary tests | Duplicate IDs across pages, empty final page, initial-load retry and sort/filter reset are covered by Flutter regressions. These were reported passing in the 31-test suite at run #797; the later exact-head A3.4 suite also passed. | VERIFIED by prior CI; preserve A3.4 baseline |
| 3 | Maale localization | Owner-approved architecture excludes new Maale translations from this release. New UI and seed data remain Amharic-first with English secondary. Legacy Maale database columns are preserved without invented translations. | OUT OF SCOPE by approved architecture |
| 4 | Seller phone ownership / OTP | No durable, genuinely no-cost live SMS delivery agreement is evidenced. SMSHub's limited KYC-dependent trial credits are not a durable no-cost service; Africa's Talking sandbox does not deliver to real handsets. No provider integration or OTP simulation is permitted. The system must not label a number verified without real delivery and verification evidence. | BLOCKED — external provider agreement |
| 5 | Private intelligence integration | The marketplace core must remain independent of IROKA/private intelligence. No approved provider contract, credentials or SDK is available. Do not add a fabricated provider integration or make core marketplace workflows depend on it. The integration remains optional and disabled until an approved service contract and interface are supplied. | DEFERRED — optional external integration; not a core A3 completion dependency |
| 6 | Operational media persistence | Provider-neutral S3 adapter and backup/restore inventory tooling are implemented and tested against S3-compatible test infrastructure. No Ethiopia-located, no-cost persistent object-storage provider, production bucket, credentials, or successful restore drill is evidenced. Do not substitute a non-Ethiopia region for personal data. | BLOCKED — data-residency and storage-provider evidence |
| 7 | Accessibility and localization acceptance | Automated analysis/widget tests are engineering evidence only. Screen-reader/TalkBack, 200% text scaling, keyboard/focus, contrast, offline/slow-network, Amharic native review and device-specific checks require real acceptance sessions and records. Maale remains out of scope. | A4 — NOT RUN / NOT ACCEPTED |
| 8 | Security and privacy acceptance | Code-level authorization, audit, report and consent workflows have regression evidence. Independent security review, evidence-attachment abuse testing, retention/deletion decisions, DPIA, processor/DPO assessment, privacy notice, processing records, incident response and Ethiopian legal review require competent review and documented evidence. | A4/legal gate — PARTIAL; NOT ACCEPTED |
| 9 | Release signing | Test APKs use ephemeral CI signing only. Owner-held production keystore generation/configuration and a gated manual App Bundle workflow are prepared. No production key, secrets, protected environment, approved permanent application ID or signed production artifact exists. Do not create/store production signing secrets in this work. | A5 prerequisite — NOT CONFIGURED; production signing NOT RUN |
| 10 | Production privacy gates | Startup/release gates fail closed unless residency, legal, privacy and phone-verification attestations are explicitly supplied. The flags are controls, not evidence that the conditions are met. Current production attestations remain false/unknown. | A5 prerequisite — BLOCKED; no production activation |

## Other A3 engineering items already implemented

- Amharic-first Flutter application shell and English secondary locale.
- Public marketplace discovery, bounded search, sorting and pagination.
- Seller identity/listing lifecycle, inquiries, offline drafts and synchronization.
- Listing image validation, ownership checks, idempotent media IDs and provider-neutral adapter.
- Moderation, audit, reports/complaints, suspension/reinstatement and consent-controlled job-seeker workflows.
- Owner-governed employment-provider and advertising lifecycle.
- Market directory and weekly schedule: eight owner-provided market/day records; public schedule/search/filter APIs; administrator CRUD and audit; React management; Flutter calendar and offline cache.
- Backend, admin and Flutter locked dependencies, lint/build/test gates and Android staging build.

The committed `admin/package-lock.json` is present on this branch. The older register sentence saying it exists only as a CI artifact is superseded and must not be used as current state.

## A3.4 closed baseline — do not reopen

A3.4 engineering verification remains **VERIFIED-CLOSED** at application-code SHA `6221e790f2faf4fcd61b1950d8950c4a26002716`, CI run #1129. The run verified backend (98 tests; PostgreSQL integration 2; S3 integration 3; Ruff and lock checks), admin (4 tests, build and audit), Flutter (44 tests and analysis), and Android staging universal debug APK artifact ID `15122113305`. The artifact ZIP and APK SHA-256 values are preserved in the A3.4 closure addendum. The later docs-only closure commit does not replace the exact application-code verification.

Physical-device acceptance, TalkBack, broader system acceptance and field-pilot review are explicitly A4 and were NOT performed by A3.4.

## Remaining actions and acceptance ownership

1. **A3 repository engineering:** The core feature implementation and automated engineering verification described above are present. Any further code defect must be tied to a reproducible failing test or concrete requirement; do not invent additional scope.
2. **Isolated Neon migration test:** NOT RUN. Requires confirmation of the exact isolated test branch, its no-cost status and authorization to apply the migration there. Never target production.
3. **A4:** Execute the physical-device/accessibility matrix, end-to-end staging acceptance, field-pilot catalogue review, and independent security/privacy review. Record tester/device/environment, exact build SHA, expected/actual result and evidence.
4. **External legal/data prerequisites:** Obtain Ethiopia data-residency evidence for database, object storage, logs and backups; privacy/legal documents and competent review; and a durable no-cost live SMS agreement if phone ownership verification remains a required launch capability.
5. **Optional private intelligence:** Remains disabled until an approved service contract, provider interface, credentials and privacy/security review exist.
6. **A5:** Production signing, production data activation, deployment, public distribution and commercial operation remain separate Owner-authorized activities.

## Status

- A1: VERIFIED-CLOSED.
- A2: VERIFIED-CLOSED at frozen `main` SHA `1e0dc04d66b0b80b29ce81b28084c1d8211ce708`.
- A3.4: VERIFIED-CLOSED; preserve exact evidence above.
- Overall A3: ENGINEERING IMPLEMENTATION SUBSTANTIALLY COMPLETE; register remains OPEN pending any separately authorized isolated Neon migration evidence and Owner disposition of non-A3/external gates. This record is not an overall A3 closure certificate.
- A4: NOT STARTED / NOT ACCEPTED.
- A5: NOT AUTHORIZED / NOT STARTED.
- Merge, modification of `main`, production migrations, deployment, production signing, payments, paid providers and commercial activation: NOT AUTHORIZED.

No paid plan, card, top-up, deposit or paid-service activation is part of this resolution.
