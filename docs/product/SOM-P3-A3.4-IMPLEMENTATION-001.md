# A3.4 — Engineering Verification Implementation Record

**Record:** SOM-P3-A3.4-IMPLEMENTATION-001  
**Status:** VERIFIED-CLOSED — A3.4 engineering-verification scope complete  
**Owner-approved scope:** Strengthen regression tests; make dependency resolution reproducible; broaden linting; produce exact-head CI evidence.  
**Repository:** `akefadaka-git/south-omo-market`  
**Branch:** `feat/customer-platform-foundation`  
**Verified application/code head:** `6221e790f2faf4fcd61b1950d8950c4a26002716`  
**CI run:** [Workflow run #1129](https://github.com/akefadaka-git/south-omo-market/actions/runs/45830363627) — SUCCESS (run ID `45830363627`, attempt 1)

## 1. Scope delivered

### Dependency reproducibility

- Committed `backend/uv.lock`, `admin/package-lock.json`, and `mobile/pubspec.lock`.
- Backend CI verifies the lock with `uv lock --check`, installs with `uv sync --locked --extra dev`, and runs commands through `uv run --locked`.
- Admin CI uses `npm ci --install-strategy=nested` against the committed npm lockfile and runs `npm audit --audit-level=high`.
- Flutter CI uses `flutter pub get --enforce-lockfile` for analysis, tests, and the Android staging build.
- Android scaffold generation uses `flutter create ... --no-pub` before the enforced locked dependency resolution, preventing an implicit unlocked resolution during scaffold generation.

### Linting

- Backend Ruff configuration now explicitly selects `E4`, `E7`, `E9`, `F`, and `I` rules.
- CI runs the complete configured check over `backend/app` and `backend/tests`, rather than the former critical-error-only subset.
- Safe Ruff fixes were applied across 24 backend files and rechecked successfully.
- Temporary lock-generation and lint-autofix workflows were removed after use; they are not retained as ongoing privileged maintenance paths.

### Regression and integration verification

The exact-head workflow ran the backend, PostgreSQL, object-storage, admin, and Flutter suites. The accumulated regression coverage includes seller/business authorization and onboarding, buyer contact-consent privacy, listing lifecycle and moderation, offline synchronization, migration-chain behavior, and the mobile/admin user flows. This record reports the suite outcomes from the exact-head run; it does not claim that every test was newly authored in A3.4.

## 2. Exact-head CI evidence

- Run number: **1129**
- Run ID: `45830363627`
- Attempt: **1**
- Event: push
- Branch: `feat/customer-platform-foundation`
- Head SHA: `6221e790f2faf4fcd61b1950d8950c4a26002716`
- Started: 2026-11-26 13:33:54 UTC
- Completed: 2026-11-26 13:38:47 UTC
- Overall conclusion: **SUCCESS**

| Job / check | Exact result |
|---|---|
| Backend lock check | PASS — `uv lock --check` |
| Backend locked install | PASS — `uv sync --locked --extra dev` |
| Backend Ruff | PASS — “All checks passed!” |
| Backend regression suite | **98 passed, 23 warnings, 0 failures** |
| PostgreSQL migration/audit integration | **2 passed, 4 warnings** |
| S3-compatible storage integration | **3 passed** |
| Admin locked install | PASS — `npm ci` |
| Admin dependency audit | PASS — `npm audit --audit-level=high` |
| Admin build | PASS |
| Admin tests | **2 test files, 4 tests passed** |
| Flutter enforced-lock analysis | PASS |
| Flutter tests | **44 passed** |
| Android staging readiness | PASS — HTTPS origin and `/ready` database readiness gate |
| Android staging debug build | PASS — universal `app-debug.apk` built |
| Android staging artifact upload | PASS |
| Android production release | SKIPPED — release configuration gate not enabled |

The workflow run is exact-head evidence for the application/code SHA above. The subsequent A3.4 records/register update is documentation-only and does not change application code or the tested dependency configuration.

## 3. Android staging artifact integrity

- Artifact: `south-omo-market-android-staging-universal-apk`
- Artifact ID: `15122113305`
- [GitHub Actions artifact](https://github.com/akefadaka-git/south-omo-market/actions/runs/45830363627/artifacts/15122113305)
- GitHub artifact ZIP size: **70,993,826 bytes**
- GitHub published ZIP digest: `sha256:127e51da0c56e3728c79a037cd33c25d96c477922dad0dfc2717790cc18ff57d`
- Downloaded ZIP size: **70,993,826 bytes**
- Independently calculated ZIP SHA-256: `127e51da0c56e3728c79a037cd33c25d96c477922dad0dfc2717790cc18ff57d` — MATCH
- ZIP contents: exactly one `app-debug.apk`
- APK size: **146,514,575 bytes**
- Independently calculated APK SHA-256: `e8dfb9ded45c1da3c944af0387ca8153fa94a6522ba3c59b66ad9ac6c4cde690`

The staging job log confirms the APK build and successful upload. This is a staging/debug artifact, not a production-signed APK. Physical-device installation and runtime acceptance are NOT RUN. The artifact is subject to GitHub's 14-day retention and is not a permanent release distribution.

## 4. A3.4 commit evidence

The A3.4 engineering-verification changes on the branch include:

- `6b4805896afe87fb929b34d7c6f84b0a7d36553f` — generate reproducible dependency lockfiles.
- `dc982223c81f106831448731a884e6550558318b` — commit generated lockfiles.
- `2be05fb554e0200eb2fd79cea7eccecca1119fb4` — pin backend, admin, and mobile dependencies.
- `e34ce8ada364ecbababbb0fad64782180bd98d61` — enforce locked dependencies and full backend lint in CI.
- `73acaf2405190fd52f4112e77309e12b1dfee8b4` — define explicit backend lint rules.
- `9aba6c94c1c2aa975373e01f499c5d3080eded7a` — apply safe backend lint fixes.
- `4d4b0e490a543557191912ab7d770e3e7d241041` — remove temporary dependency lock generator.
- `2367f16941049a23ab269567de24a46aed599b73` — remove temporary lint-autofix workflow.
- `6221e790f2faf4fcd61b1950d8950c4a26002716` — enforce Flutter lockfile resolution in Android staging build.

## 5. Scope boundaries and qualifications

- The PostgreSQL migration and audit integration tests ran against the CI service database only. No shared, staging, or production database migration was executed.
- The staging readiness probe verified the configured HTTPS staging API and its database readiness response; it is not a full production or field acceptance test.
- Lockfile-enforced dependency installation and CI build success are verified. Bit-for-bit identical APK reproduction across independent clean runners was not separately tested and is not claimed.
- No physical Android device acceptance, accessibility field review, independent security/legal review, or commercial operations acceptance is claimed.
- No merge, deployment, production release, production signing, shared database migration, or commercial activation occurred.
- `main` remains unchanged. PR #1 remains open/draft/unmerged.

## 6. Stage status

- A3.4 Engineering Verification: **VERIFIED-CLOSED** — this work item only.
- A3 overall: **IN PROGRESS / OPEN** — other A3 work and broader platform acceptance remain separate.
- A4: **NOT STARTED** — system-level verification remains a separate stage.
- A5: **NOT AUTHORIZED / NOT STARTED** — deployment remains separately gated.

