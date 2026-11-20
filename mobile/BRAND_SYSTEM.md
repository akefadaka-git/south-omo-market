# South Omo Market — mobile brand system

## Brand experience
The app uses a river-basin identity: deep river ink, forest green, jade, mint, warm earth and sunrise gold. The mark is original vector artwork drawn in Flutter, with a flowing water stroke, ridge lines and rising sun.

## Dedicated semantic icon pack
`market_icon_pack.dart` defines consistent catalogue and action glyphs and a reusable accessible category tile. Category mappings are centralized to prevent arbitrary per-screen icon choices.

## Welcome and about surfaces
`MarketWelcomePage` provides a warm, dark branded welcome experience. `MarketAboutPage` explains the local marketplace purpose and links to the welcome surface. The discovery app bar exposes the About page.

## Catalogue browsing and account surfaces
The discovery screen opens a grouped catalogue browser for the six API-backed market groups, with curated subcategory shortcuts that refine local results. Search now includes listing descriptions and category labels. Seller sign-in/profile setup and buyer authentication use the shared brand surfaces and clearer form affordances. The backend still exposes broad categories only; subcategory choices are client-side refinements, not persisted taxonomy IDs.

## Amharic typography
The theme explicitly requests Noto Sans Ethiopic through font-family fallback. The app now bundles the official hinted Noto Sans Ethiopic Regular TTF from the Noto Fonts project and registers it as the `NotoSansEthiopic` Flutter font family. The upstream SIL Open Font License 1.1 notice is included at `assets/fonts/OFL.txt`. Latin text continues to use the platform's primary sans-serif face; Ethiopic glyphs use the bundled fallback. Visual QA on target Android devices remains required.

## Verification boundary
Widget tests cover the icon mapping and welcome/about navigation. CI and physical-device checks are required for final visual, contrast, TalkBack, large-text and Samsung Galaxy A16 acceptance.
