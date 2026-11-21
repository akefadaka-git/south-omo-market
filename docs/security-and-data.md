# Security and data baseline

Use synthetic data only. Never place real customer, seller, identity or transaction data in development, tests, fixtures, screenshots or CI artifacts.

Store password hashes only; never log passwords or tokens. Enforce authorization and resource ownership server-side. Apply least privilege to administrative actions. Add an append-only audit trail for sensitive administrative actions.

Validate requests and uploaded media type, size and content. Rate-limit authentication, inquiry and report endpoints before public launch. Keep secrets in environment variables; commit placeholders only. Do not enable public uploads until storage, scanning, retention and abuse controls are reviewed.

Before real customer data, document data categories, purposes, lawful basis, access, retention, deletion, incident handling and applicable Ethiopian legal requirements. Hosting/data-location must be resolved before production data.

HTTPS, production secrets, backups, restore testing, monitoring, vulnerability review and incident response are required before deployment. This is not a legal compliance certification.
