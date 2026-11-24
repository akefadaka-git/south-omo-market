# A3 — Owner governance, employment agency and AI policy foundation

Status: implementation in progress; exact-head GitHub Actions run #877 PASS on `13c888060debd753083a5c3da67383f038f9f2b9`.
Target: `feat/a3-platform-foundation`; no production database or deployment changes.

## Migration and ORM

Alembic revision `0011_owner_governance_employment_ai` follows `0010_market_schedule_effectivity`. Revisions `0001–0010` remain immutable. It adds:

- RBAC: roles, permissions, role permissions, user roles and direct user permission grants.
- Business identity: business profiles and active/pending memberships.
- Employment agency: verified providers, private job-seeker profiles, opportunities, agreements, payment evidence, advertisements, applications, consent, candidate referrals and event history.
- Policy governance: versioned policy packs and rules.
- AI governance: provider/model registry and task routes with allowlist, enabled/configured, classification, quota and human-approval fields.

ORM mappings are registered in Alembic metadata through `app.governance_models`.

## Owner authority and permissions

- `is_admin` is retained for legacy compatibility and is not an Owner grant.
- Owner-only capabilities are checked against the explicit `owner` role, not the legacy admin flag or direct user-permission overrides.
- The system reference seeder creates the Owner role and its permission definitions but never creates a user or assigns the role.
- Initial Owner assignment is a protected, interactive out-of-band operation: `python -m app.owner_cli --operator <authenticated-operator-id>`. It requires an existing account, exact phone confirmation and the explicit `ASSIGN-OWNER` phrase. The operation is serialized with a PostgreSQL advisory transaction lock and audited.
- The reference seeder is run separately after migrations: `python -m app.seed_cli`.

## Employment agency workflow

1. An authenticated account submits `POST /employment/providers/request`; the business profile, provider record and owner membership begin pending. Duplicate requests for the same account are rejected.
2. Owner reviews pending requests through the Owner-only provider queue. Owner may reject with a recorded reason (provider and membership become rejected) or verify provider identity/business information; verification activates the pending business-owner membership.
3. Owner prepares the opportunity, price, duration and versioned advertising agreement.
4. An active provider business member accepts the agreement with recorded acceptance evidence.
5. The provider submits direct-payment evidence; no gateway is enabled.
6. Owner verifies the payment evidence.
7. Owner publishes only when provider verification, agreement acceptance and verified payment coverage all pass. Underpayment is rejected.
8. Published ads expire at the agreed end date. Public discovery returns published, unexpired opportunities only.

Ordinary seller listing create/update/offline-sync is blocked for the `work-opportunities` category and every descendant. Ordinary admins do not receive the Owner-only employment permissions. Job-seeker profiles are private by default; the profile endpoint ignores attempts to set public visibility.

IROKA matching is not an autonomous hiring or eligibility decision. Candidate referrals are constrained to a human-review decision state in the schema. Employer access to private profiles requires a future explicit consent/referral workflow.

## AI provider and policy defaults

- IROKA is the designated primary provider record, but `enabled=false` and `endpoint_configured=false` until an approved endpoint and contract exist.
- The secondary provider placeholder is disabled and not allowlisted.
- AI model/task execution is not activated. Task routes are empty/disabled by default; policy pack default effect is deny.
- AI provider/model configuration is Owner-only. Human approval is required by default for AI task routes.
- No secrets or model credentials are seeded.

## Seed guarantees

`app.seeders.system_reference.seed_system_reference_data` uses deterministic IDs and upserts stable system codes. Re-running it is intended to be idempotent. It does not overwrite business translations or create real users, provider accounts, advertisements, jobs, payment records, or credentials. It does not assign Owner or Admin roles to a person.

## Verification and activation gates

- Automated tests cover migration head, schema presence, idempotent reference seeding, Owner permission mapping, absence of default Owner assignments, IROKA placeholder state, provider-request pending state/duplicate rejection, consent withdrawal across multiple purposes, and the full PostgreSQL Owner-controlled advertising lifecycle.
- Exact-head CI run #877 PASS: backend Ruff; 45 backend pytest tests; 2 PostgreSQL migration/audit/employment lifecycle tests (including provider queue, rejection and paid-ad publication); 3 S3 storage tests; admin dependency audit (0 vulnerabilities), production build and 2 Vitest files/3 tests; Flutter analysis and 34 tests; Android staging readiness check and three-ABI debug APK artifact. Production release APK remains skipped.
- The Neon `south-omo-testing` branch remains the intended test database. This implementation has not run Alembic or seeders against Neon.
- Production Neon branch, deployment, merge, public commercial launch, real provider/payment data, and live AI integration remain outside this authorization.
- Employment agency licensing, recruitment and consumer/employment obligations require legal review before paid commercial activation.
