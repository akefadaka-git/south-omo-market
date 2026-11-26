# A3.3 — Versioned Listing Edits and Material-Change Moderation

**Record:** SOM-P3-A3.3-001  
**Status:** IMPLEMENTED — CI PASS; endpoint-level acceptance tests still required before A3.3 closure  
**Branch:** `feat/customer-platform-foundation`

## Behavior

- Draft listings retain the existing direct-edit workflow.
- Published listing edits are stored as proposed values in a separate `listing_edits` record; the public listing remains unchanged while review is pending.
- Only description formatting changes that preserve the exact Unicode word-token sequence (case, whitespace, and punctuation normalization) publish directly. These are audit-logged. Wording, claims, prices, identity, category, attributes, and location changes require moderation.
- A database uniqueness constraint permits at most one pending edit per listing, including concurrent submissions.
- Admins receive a dedicated pending edit queue and approve/reject endpoint. Approval rechecks active verified business and seller membership, plus active category/location references. Rejection leaves the currently published listing unchanged.
- Every approval, rejection, and direct minor correction creates an audit event.

## Verification status

- Latest full CI: [run #45717182912](https://github.com/akefadaka-git/south-omo-market/actions/runs/45717182912), head `486f67439c93d9dd6ad751f1e622014b389744c4` — SUCCESS.
- Backend pytest: 91 passed; PostgreSQL full migration-chain integration: 2 passed; Ruff passed.
- Migration `0021_listing_edit_versions` is included in the CI migration-chain test.
- The current dedicated A3.3 tests cover the minor-text classifier and migration-chain expectation. Endpoint-level API tests for seller submission, duplicate pending edit, admin approval/rejection, audit events, and preservation of the public listing while pending remain outstanding. Therefore A3.3 is not yet VERIFIED-CLOSED.

## Scope boundaries

No chat, payments, delivery, subscriptions, paid promotion, analytics expansion, deployment, merge, or shared database migration is included. Migration is CI-tested only.
