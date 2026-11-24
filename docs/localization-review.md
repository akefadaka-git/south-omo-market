# Localization review and integration register

**Status:** PARTIAL / HUMAN REVIEW REQUIRED. This file does not certify any translation as approved.

## Language policy

- English: technical fallback and secondary interface language.
- Amharic: primary interface language. New report workflow labels have provisional Amharic strings in `mobile/lib/features/marketplace/listing_detail_page.dart`, `mobile/lib/features/marketplace/my_reports_page.dart` and `mobile/lib/l10n/market_strings.dart`.
- Maale (MDY): no human-approved translation set has been supplied. The shared `marketString` helper falls back to English when an MDY string is empty. Do not enable a Maale language selector or claim Maale support until the complete glossary, UI strings, legal notices and font/script acceptance are approved.

## Review register

| Area | Integration | Review state |
|---|---|---|
| Core app navigation and marketplace | Existing English/Amharic shared string layer | Amharic review pending |
| Report and complaint workflow | Report actions, reasons, evidence fields, statuses and My Reports screen have English/Amharic strings | Provisional; native-speaker review pending |
| Category catalogue | English category names and schemas | Amharic and Maale terminology pending; no fabricated translations |
| Seller forms and validation | Schema labels currently fall back to English when localized labels are absent | Human translation and terminology review pending |
| Privacy notice, terms and seller rules | Not yet published | Legal translation and approval missing |
| Dates, numbers, prices and location names | Existing locale-aware formatting needs a full screen-by-screen check | Acceptance pending |
| Fonts and script rendering | Noto Sans Ethiopic is bundled | Maale script/font compatibility not established |

## Required human-review process

1. Recruit at least two independent Amharic reviewers familiar with marketplace terminology and one designated terminology owner.
2. Build a source-string export with stable keys, context, character limits and screenshots.
3. Record preferred Amharic term, rejected alternatives, reviewer, date and approval status.
4. For Maale, appoint fluent native speakers who can validate the target orthography/script and dialect choices; record approved glyph/font requirements and test on low-cost Android devices.
5. Translate legal/privacy notices only after Ethiopian counsel approves the English legal source.
6. Test truncation, right-to-left/bidirectional mixed text, search normalization, screen readers, font scaling and offline catalogue labels.
7. Do not mark a string set complete until reviewers sign the terminology and screen acceptance register.

## Release gate

A4 localization acceptance requires reviewer identities/roles, approved terminology, complete translated string coverage, no blank labels, script/font rendering evidence and physical-device screenshots. Until then Amharic labels added in the report flow remain provisional and Maale remains NOT IMPLEMENTED.
