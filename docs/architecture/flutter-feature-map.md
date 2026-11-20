# Flutter application structure and localization

## Feature-oriented module layout

The Flutter entrypoint is intentionally small. main.dart starts the application and exposes stable public imports for existing tests; app/market_app.dart owns the root Material application, locale state and launch transition.

- features/marketplace/: public discovery, listing details, seller listing/profile management and buyer authentication.
- features/seller/: seller sign-in/registration, inquiry inbox and offline draft/photo queue.
- design/: shared brand identity, design tokens, typography, iconography, category browser and reusable presentation components.
- l10n/: locale-aware copy and shared status-label mapping.
- data/: local draft persistence and retryable offline synchronization.

The root marketplace_pages.dart and feature page barrels are retained to avoid breaking existing imports while the app moves to feature-owned files. New screens should be placed in their owning feature folder rather than returned to the legacy root files.

## Locale policy

Amharic (am) is the default app locale. English (en) is an explicit secondary choice. Customer-facing copy, form validation, error states, category subtopics, seller workflow messages and marketplace statuses are localized for Amharic.

Maale (mdy) is not yet a selectable application locale because reviewed Maale translations have not been supplied. Empty Maale entries must not be presented as completed translation work or silently shown as machine-generated Maale. A human-reviewed Maale translation and terminology pass remains a separate localization gate.

## Verification boundary

Automated widget tests cover the default Amharic launch flow, explicit English selection, seller registration entry, category-browser copy and localized workflow statuses. CI verifies compilation and widget behavior; it does not replace human linguistic review or physical-device layout/accessibility acceptance.
