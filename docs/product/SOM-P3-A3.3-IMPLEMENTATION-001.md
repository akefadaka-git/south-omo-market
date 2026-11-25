# A3.3 — Versioned Listing Edits and Material-Change Moderation

**Record:** SOM-P3-A3.3-001  
**Status:** IMPLEMENTED — awaiting GitHub Actions verification  
**Branch:** `feat/customer-platform-foundation`

## Behavior

- Draft listings retain the existing direct-edit workflow.
- Published listing edits are stored as proposed values in a separate `listing_edits` record; the public listing remains unchanged while review is pending.
- Only description formatting changes that preserve the exact Unicode word-token sequence (case, whitespace, and punctuation normalization) publish directly. These are audit-logged. Wording, claims, prices, identity, category, attributes, and location changes require moderation.
- A database uniqueness constraint permits at most one pending edit per listing, including concurrent submissions.
- Admins receive a dedicated pending edit queue and approve/reject endpoint. Approval rechecks active verified business and seller membership, plus active category/location references. Rejection leaves the currently published listing unchanged.
- Every approval, rejection, and direct minor correction creates an audit event.

## Scope boundaries

No chat, payments, delivery, subscriptions, paid promotion, analytics expansion, deployment, merge, or shared database migration is included. Migration is CI-tested only.
