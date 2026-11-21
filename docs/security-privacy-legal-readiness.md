# Security, privacy and legal readiness — South Omo Market

**Status:** OPEN / NOT LEGALLY CLEARED. This is an engineering readiness register, not legal advice or a legal opinion.

## Executive finding — data residency is a release blocker

The Personal Data Protection Proclamation No. 1321/2024 is listed as in force by Ethiopia's Ministry of Justice. Article 22(1) requires a controller or processor to ensure that locally collected or obtained personal data are stored on a server or data centre located in Ethiopia. Article 21 addresses safeguards before cross-border transfers; Article 22(3) requires prior Authority approval for cross-border transfer of sensitive personal data.

The existing Neon and Render test configuration is in Singapore. It is permitted here only for synthetic, non-personal test data. Do not load real user accounts, phone numbers, inquiries, reports, seller information, listing photographs that identify people, or other personal data into that environment. Cloudflare R2's published bucket locations do not identify an Ethiopia location; its free tier therefore is not an approved production store for local personal data. A provider's free allowance does not override the data-residency requirement.

**Go/no-go:** no production collection or processing of real personal data until the owner has an Ethiopia-located database and object-storage arrangement, or Ethiopian counsel and the competent Authority have confirmed a lawful cross-border arrangement in writing. Sensitive personal data must not be transferred abroad without the required prior approval.

Official sources:
- Ministry of Justice: Personal Data Protection Proclamation No. 1321/2024 — https://justice.gov.et/en/law/personal-data-protection-proclamation/
- Federal Negarit Gazette / Ethiopian Communications Authority copy — https://pdp.eca.et/files/pdfs/pdp-proclamation/pdp_personal_data_protection_proclamation_No_1321_2024.pdf
- Cloudflare R2 bucket locations — https://developers.cloudflare.com/api/resources/r2/subresources/buckets/

## Current personal-data inventory

| Data | Why the platform holds it | Key controls / open work |
|---|---|---|
| User phone number and display name | Account identity, buyer/seller contact | Authentication and access controls exist; no verified phone ownership yet; retention and correction/deletion process open |
| Password hash and access-token subject | Authentication | Password hashes and short-lived signed access tokens; independent security review and credential lifecycle review open |
| Seller profile and location | Seller identity and marketplace trust | Seller account access controls; data residency and disclosure/retention review open |
| Listing text, price, category and location | Marketplace discovery | Public only after moderation; personal data may be included by sellers; privacy notice and removal process open |
| Listing photographs | Marketplace product presentation | Image validation and ownership checks exist; storage provider must be Ethiopia-located for any personal data; evidence and deletion lifecycle open |
| Buyer inquiry name, phone/contact value and message | Buyer-to-seller communication | Authenticated inquiry workflow; communications content/metadata may be sensitive under the Proclamation; minimization and retention review open |
| Abuse reports and evidence | Trust, safety and dispute investigation | Report workflow exists; evidence currently text-only; access policy, retention, legal holds and deletion workflow open |
| Audit events | Security and moderation accountability | Append-only audit mechanism exists; retention, access, export and minimization policy open |

Do not collect Fayda numbers, identity-document images, precise location traces, biometric information, health information or other sensitive personal data unless a separate lawful purpose, necessity assessment, safeguards and required authorization have been approved.

## Legal and compliance work register

| Requirement / issue | Engineering or operational evidence needed | State |
|---|---|---|
| Controller/processor roles and lawful basis | Identify the legal entity operating the marketplace; document each processing purpose and lawful basis; define platform vs seller roles and processor contracts | MISSING |
| Data sovereignty (Article 22) | Ethiopia-located database, object storage, logs, backups and disaster-recovery copies; document vendor locations and subprocessors | BLOCKER |
| Cross-border transfer (Articles 21–22) | Map every transfer and remote access; obtain counsel/Authority decision and prior approval where required, especially sensitive data | MISSING |
| Privacy notice / transparency (Article 24) | Publish controller identity/contact, representative and DPO contacts, purposes, lawful bases, required/optional data, consequences, recipients, transfers, retention, rights, consent withdrawal and complaint route | MISSING |
| Data subject rights | Implement and test access, correction, objection/withdrawal where applicable, and secure erasure; identify exceptions and legal holds | MISSING |
| Data protection impact assessment (Articles 42 and 47) | Complete a DPIA covering location data, marketplace messaging, public listings, reports/evidence, children/minors and provider transfers | MISSING |
| Data Protection Officer (Articles 40–42) | Determine applicability and formally designate/contact a DPO as required | MISSING |
| Processing records (Article 42) | Maintain a record of processing activities, data categories, purposes, recipients, locations, retention and safeguards | MISSING |
| Security (Articles 17 and 42) | Independent penetration/security review, least privilege, secret rotation, encryption, monitoring, recovery test and regular control assessment | PARTIAL |
| Breach notification (Article 43) | Incident response plan and on-call owner process capable of notifying the Authority within 72 hours after awareness, with required incident details | MISSING |
| Retention and destruction (Article 50) | Approve purpose-specific retention schedule; delete or irreversibly destroy data when the purpose expires, subject to lawful holds; propagate deletion to processors and backups | MISSING |
| Electronic transaction / intermediary duties | Counsel review of Electronic Transaction Proclamation No. 1205/2020, including complaint/takedown handling and intermediary status | MISSING |
| Consumer and seller obligations | Counsel review of Trade Competition and Consumers Protection Proclamation No. 813/2014, seller disclosures, prohibited products, pricing, refunds, receipts and complaint escalation | MISSING |
| Sector-specific requirements | Review livestock, veterinary products, food, rentals, transport, jobs and regulated goods/services before enabling each category | MISSING |
| Children and vulnerable users | Determine age policy, child-data processing limits, guardian/consent requirements and reporting escalation | MISSING |
| Terms and platform rules | Draft and approve terms, seller terms, buyer terms, prohibited-items policy, complaint/takedown policy, refunds/disputes policy and privacy notice | MISSING |

The Ministry of Justice lists the older Trade Practice and Consumers' Protection Proclamation No. 685/2010 as repealed and lists Trade Competition and Consumers Protection Proclamation No. 813/2014 as in force. Counsel must confirm all amendments, implementing directives and applicability before launch.

## Security controls already present in the codebase

- Password hashing and bearer-token authentication.
- Per-request user active/suspension checks; suspended seller accounts cannot continue using existing bearer tokens.
- Admin-only moderation and report-review endpoints.
- Append-only audit event protection at the database layer.
- Listing ownership checks and public visibility restricted to published listings.
- Image file-type validation, decode/re-encode, byte/pixel limits and private storage adapter.
- Production settings require a strong JWT secret, HTTPS S3 endpoint/TLS and shared Redis rate-limit storage.
- Encrypted PostgreSQL/object backup script with checksums and non-destructive restore validation.

These controls are not a substitute for a security assessment or evidence of production configuration.

Production configuration now fails closed unless the owner supplies an Ethiopia residency attestation and evidence reference, legal-review approval, an HTTPS privacy-notice URL, completed DPIA and processing records, a documented DPO applicability assessment (and contact if appointment is required), and an explicit seller-phone-verification readiness attestation. The flags do not validate the evidence themselves; counsel/owner sign-off and provider-location evidence remain mandatory.

## Required next controls before real users

1. Keep all current Singapore-hosted environments synthetic-only.
2. Select an Ethiopia-located hosting/data-centre provider for database, object storage, logs and backups; verify contract, subprocessor, support-access and backup locations.
3. Complete data-flow map, controller/processor analysis, lawful-basis register, DPIA, privacy notice and processing record.
4. Define data-subject access/correction/deletion workflow, retention periods and legal-hold exceptions.
5. Define incident severity, evidence preservation, containment, owner escalation and 72-hour regulatory notification procedure.
6. Complete independent security review and test authorization boundaries, report privacy, seller suspension, IDOR, rate limits, file uploads and secret handling.
7. Obtain Ethiopian legal review for electronic marketplace, seller verification, consumer protection, prohibited goods and all regulated category groups.
8. Do not enable production personal-data collection until the data-residency blocker is cleared in writing.

## Governance

- This document does not authorize deployment or data migration.
- No production secrets, identity documents, personal records or real marketplace data are to be placed in source control or chat.
- A4 verification and A5 deployment remain separate owner approval gates.
