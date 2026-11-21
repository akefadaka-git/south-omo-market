# Accessibility and physical Android acceptance

**Status:** PARTIAL / NOT ACCEPTED. Widget tests and semantic labels are not equivalent to physical-device or assistive-technology acceptance. The report-error visibility and Maale English-fallback regression tests are added; execution on the latest accessibility changes is pending.

## Baseline target

Use WCAG 2.2 AA as the web/admin and mobile interaction reference, plus Android platform accessibility guidance. The app is intended for affordable Android phones, variable connectivity and Amharic-first use.

## Automated and code-level checks

- Run `flutter analyze --no-fatal-infos` and the complete Flutter widget/unit test suite.
- Run admin TypeScript build and test suite.
- Verify every actionable icon has a tooltip/semantic label; every form field has a persistent label and field-level validation; errors use `Semantics(liveRegion: true)` or an equivalent announced state where appropriate.
- Verify focus order, keyboard traversal, dialogs, back navigation and no keyboard-only traps.
- Test 200% text scaling and display-size changes without clipped critical actions or inaccessible content.
- Check foreground/background contrast for normal and large text, disabled controls, focus indicators and error/status states.
- Verify touch targets are comfortably usable (target at least 48 dp where practical).
- Verify no information is conveyed by color alone; statuses include text.
- Check that Amharic Ethiopic glyphs render with no tofu/missing glyphs and that mixed Latin/digits/phone numbers have readable bidirectional layout.
- Ensure loading, success, empty, retry and error states are announced to TalkBack.

## Physical-device acceptance matrix

| Device / condition | Required scenarios | State |
|---|---|---|
| Low-cost Android, current supported OS | Install, sign-in, browse, seller draft, upload, inquiry, report and My Reports | NOT RUN |
| TalkBack enabled | Navigate discovery, listing detail, report form, evidence fields, status cards and seller inbox | NOT RUN |
| Large font / display size | All screens, forms, dialogs, tables/cards, admin mobile viewport | NOT RUN |
| Slow 2G / intermittent network | Search, pagination, retry, draft save, sync retry, media retry and report submission | NOT RUN |
| Offline / airplane mode | Cached category schema, local drafts, queued uploads, no false success for remote report submission | NOT RUN |
| Low storage / permission denied | Camera/gallery denial, image decode failure, storage quota and graceful recovery | NOT RUN |
| Amharic locale | All labels, validation, numbers, prices, dates, category terms and mixed phone numbers | NOT RUN |
| Maale locale | Only after native-speaker translation/script/font approval | BLOCKED |
| Android lifecycle | Background/foreground, process death, app update, token expiry and retry | NOT RUN |
| Security acceptance | Suspended seller token rejection, buyer/seller ownership boundaries, report privacy and admin authorization | NOT RUN |

## Report-flow accessibility checks added

- Report listing and report seller actions use visible text labels, not icon-only controls.
- Report form fields have labels, length limits and validation.
- My Reports includes a refresh tooltip, live-region loading/error/empty states, retry action and visible status text.
- Listing-detail loading failures are separated from report/inquiry action failures; action feedback uses live regions and no longer replaces the listing content.
- Listing photographs expose a semantic label based on the listing title.
- Amharic report labels have been integrated provisionally; native-speaker review is still required.

## Acceptance evidence required

Record device model, Android version, app build SHA/version, API URL/environment, locale, font/display settings, TalkBack version, test case, expected/actual result, screenshot/video reference and tester sign-off. No physical-device acceptance is claimed by this code change.
