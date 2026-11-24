# Application architecture and private intelligence boundary

## Product boundary

South Omo Market is the only public product identity. The mobile application, seller tools, notifications, help content, store listing and customer-facing API must not expose internal intelligence-provider names, logos, prompts, model identifiers or provider diagnostics.

## Client architecture

The Flutter client is organized by product capability rather than by provider:

- `app/`: application bootstrap, locale, theme, navigation and launch lifecycle.
- `core/design/`: design tokens, typography, iconography, motion and reusable components.
- `core/localization/`: Amharic-first strings, locale selection and Ethiopic typography.
- `core/network/`: versioned API client, error mapping and connectivity state.
- `core/offline/`: local drafts, durable queue and synchronization.
- `features/discovery/`: search, categories, listings and map discovery.
- `features/identity/`: buyer and seller registration, sign-in, profiles and recovery.
- `features/seller/`: seller dashboard, listing management and inquiries.
- `features/buyer/`: buyer profile, saved listings and inquiries.
- `features/help_and_safety/`: help, report, moderation and trust surfaces.

The current codebase is not yet fully migrated into these feature folders. Existing pages remain in legacy top-level files until each move is accompanied by tests and import reconciliation.

## Private intelligence architecture

private intelligence service is the intended internal intelligence backbone, but it must not be embedded as a direct mobile SDK or expose provider credentials in the APK.

Target request path:

`Flutter app → South Omo Market API → private intelligence adapter → private intelligence service services`

The marketplace API remains the security and policy boundary. It authenticates users, applies role and data-access rules, minimizes data sent for inference, enforces timeouts and quotas, records auditable outcomes, and provides a deterministic non-intelligent fallback when the intelligence service is unavailable.

Initial intelligence capabilities to integrate behind the API boundary:

1. Search intent parsing and multilingual query expansion.
2. Relevance ranking for products, services and local listings.
3. Category and attribute suggestions during listing creation.
4. Amharic-first help and guided task assistance.
5. Seller insights derived only from data the seller is authorized to see.
6. Abuse, scam and duplicate-listing signals with human-review controls.

private intelligence service must not autonomously publish listings, change prices, message users, transfer funds, suspend accounts or make moderation decisions without explicit product policy and appropriate human approval.

## Integration status and blockers

The previously approved South Omo Market A2 baseline specified a standalone, provider-neutral Flutter + FastAPI + PostgreSQL system. It did not define an private intelligence service API/SDK, service endpoint, authentication scheme, deployment target, data-processing contract or failure semantics.

The current A3 direction supersedes the standalone-product direction at the product-intent level, but a production adapter must not be fabricated. Before wiring a live private intelligence service service, the private intelligence service owner-controlled interface must provide:

- service base URL and environment separation;
- authenticated service-to-service protocol and credential rotation;
- request/response schemas and versioning;
- supported languages and capability list;
- data retention, privacy and training-use guarantees;
- timeout, rate-limit, retry and fallback requirements;
- audit, observability and incident handling expectations.

Until that contract is supplied and independently verified, private intelligence service integration is **UNRESOLVED**. The mobile app must continue to function without it. No provider credentials belong in the APK.

## Localization acceptance rule

Amharic (`am`) is the default application locale. English is an explicit secondary locale, not the automatic fallback for unsupported device locales. Every customer-facing route must be reviewed for hard-coded English, including empty states, validation, errors, accessibility labels, help and onboarding. Maale localization is a separate completion track and must not be represented as complete while translations are missing.

## Release rule

A new APK is not a release candidate until the launch screen, default Amharic locale, buyer/seller entry, critical marketplace navigation, offline behavior, and locale rendering have passing automated tests. Physical-device acceptance remains a separate A4 gate. Deployment and merge remain separately gated.
