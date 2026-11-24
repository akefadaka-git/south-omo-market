# South Omo Market — mobile design system

## Brand direction

**Positioning:** a modern local-trade network rooted in the Omo basin.

The identity combines:
- Deep river-green and ink tones for trust and legibility.
- Jade and mint accents for growth and discovery.
- Warm clay and sun-gold accents inspired by local earth and sunlight.
- An original vector mark: layered ridge lines, a flowing river stroke and a rising sun.
- Rounded, low-noise surfaces with generous spacing and strong typographic hierarchy.

The mark is drawn in Flutter (MarketBrandMark), so it stays crisp at every density and works offline. The semantic icon vocabulary lives in MarketIcons; categories resolve to consistent symbols rather than scattered one-off icon choices.

## Typography and language

The design theme includes Noto Sans Ethiopic / NotoSansEthiopic as explicit font fallbacks for Ethiopic glyph coverage. Android system font fallback supplies Noto Sans Ethiopic on supported Android builds, while Latin text uses the platform sans-serif family.

**Packaging limitation:** the repository does not yet contain a licensed, bundled Noto Sans Ethiopic TTF/OTF asset. The current fallback is therefore device-provided, not an embedded font. A bundled font file and its licence notice must be added before claiming identical typography across every Android device or offline first-launch environment. No remote font download is required by this implementation.

Maale (mdy) strings remain blank where reviewed translations are not yet available; the app deliberately falls back to English rather than inventing Maale wording.

## Components

- MarketDesignSystem.lightTheme: palette, typography, app bars, cards, fields, buttons, chips and progress indicators.
- MarketBrandMark: original vector identity mark.
- MarketBrandPanel: abstract branded hero panel for discovery.
- MarketIcons: semantic category and action icon vocabulary.

## Accessibility and QA gates

The palette and component geometry are centralized for consistent contrast and touch targets. This is not a substitute for measured WCAG contrast verification, TalkBack testing, large-text testing, screen-size testing or physical Samsung Galaxy A16 visual acceptance. Those remain A4 verification tasks.

## Listing cards and media

- Discovery cards use the first public listing image when one is available.
- Image URLs are resolved against the configured API origin; API-provided relative paths are not guessed or rewritten.
- Missing, loading, or failed images fall back to a local category glyph over the brand palette. The card never depends on a remote placeholder image.
- The card keeps category, title, location, currency and price readable in a compact horizontal layout.
- The public listing API currently returns image metadata but does not expose seller verification or seller display-name fields in the discovery payload. The UI must not invent trust badges or seller identity; those require an explicit API contract and verified source data.
- Image caching/offline persistence, image galleries, and seller trust metadata remain separate follow-up work and must be validated against low-bandwidth device behavior.

