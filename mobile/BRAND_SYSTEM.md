# South Omo Market — mobile brand system

## Brand experience
The app uses a river-basin identity: deep river ink, forest green, jade, mint, warm earth and sunrise gold. The mark is original vector artwork drawn in Flutter, with a flowing water stroke, ridge lines and rising sun.

## Dedicated semantic icon pack
`market_icon_pack.dart` defines consistent catalogue and action glyphs and a reusable accessible category tile. Category mappings are centralized to prevent arbitrary per-screen icon choices.

## Welcome and about surfaces
`MarketWelcomePage` provides a warm, dark branded welcome experience. `MarketAboutPage` explains the local marketplace purpose and links to the welcome surface. The discovery app bar exposes the About page.

## Amharic typography
The theme explicitly requests Noto Sans Ethiopic through font-family fallback. The repository does not yet bundle a licensed Noto Sans Ethiopic font binary; rendering therefore still depends on the Android system fallback. This change does not claim cross-device font parity. Bundle the upstream licensed font file and its OFL notice in a subsequent asset-specific change before release.

## Verification boundary
Widget tests cover the icon mapping and welcome/about navigation. CI and physical-device checks are required for final visual, contrast, TalkBack, large-text and Samsung Galaxy A16 acceptance.
