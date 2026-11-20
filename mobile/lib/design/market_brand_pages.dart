import 'package:flutter/material.dart';

import 'market_design_system.dart';
import 'market_icon_pack.dart';

/// Brand-led welcome surface, reusable for onboarding and future launch flow.
class MarketWelcomePage extends StatelessWidget {
  const MarketWelcomePage({super.key, this.onExplore});

  final VoidCallback? onExplore;

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: MarketPalette.deep,
    body: SafeArea(
      child: Stack(
        children: [
          Positioned(right: -90, top: 35, child: _Orbit(size: 260, opacity: .10)),
          Positioned(left: -110, bottom: 10, child: _Orbit(size: 300, opacity: .08)),
          Padding(
            padding: const EdgeInsets.fromLTRB(26, 30, 26, 28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const MarketBrandMark(size: 68, onDark: true),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  decoration: BoxDecoration(
                    color: MarketPalette.mint.withValues(alpha: .12),
                    borderRadius: BorderRadius.circular(30),
                    border: Border.all(color: MarketPalette.mint.withValues(alpha: .28)),
                  ),
                  child: const Text('SOUTH OMO · LOCAL TRADE NETWORK',
                    style: TextStyle(color: MarketPalette.mint, fontSize: 10,
                      letterSpacing: 1.5, fontWeight: FontWeight.w800)),
                ),
                const SizedBox(height: 22),
                const Text('Closer markets.\nStronger communities.',
                  style: TextStyle(color: Colors.white, fontSize: 34,
                    height: 1.08, fontWeight: FontWeight.w800, letterSpacing: -1)),
                const SizedBox(height: 14),
                Text('Discover local products, useful services and businesses across South Omo.',
                  style: TextStyle(color: Colors.white.withValues(alpha: .78),
                    fontSize: 16, height: 1.5)),
                const SizedBox(height: 30),
                const Row(children: [
                  _WelcomePill(icon: MarketIconPack.products, label: 'Local goods'),
                  SizedBox(width: 8),
                  _WelcomePill(icon: MarketIconPack.services, label: 'Local skills'),
                ]),
                const Spacer(),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: onExplore ?? () => Navigator.of(context).maybePop(),
                    style: FilledButton.styleFrom(
                      backgroundColor: MarketPalette.sun,
                      foregroundColor: MarketPalette.deep,
                      minimumSize: const Size.fromHeight(56),
                    ),
                    child: const Text('Explore the marketplace',
                      style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class MarketAboutPage extends StatelessWidget {
  const MarketAboutPage({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('About South Omo Market')),
    body: ListView(
      padding: const EdgeInsets.all(18),
      children: [
        const MarketBrandPanel(
          title: 'Rooted here. Connected everywhere.',
          subtitle: 'A local marketplace for the people, products and skills of South Omo.',
        ),
        const SizedBox(height: 22),
        Text('Welcome to a closer marketplace',
          style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text('South Omo Market helps buyers discover local goods and services, and gives sellers a direct way to present what they offer.',
          style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: 20),
        _AboutFeature(icon: MarketIconPack.products, title: 'Local products',
          description: 'Agriculture, livestock, food, household goods and more.'),
        _AboutFeature(icon: MarketIconPack.services, title: 'Local services',
          description: 'Skilled work, repairs, rentals, farming and professional services.'),
        _AboutFeature(icon: MarketIconPack.location, title: 'South Omo first',
          description: 'Designed around local places and the realities of mobile connectivity.'),
        _AboutFeature(icon: MarketIconPack.message, title: 'Direct conversations',
          description: 'Buyers contact sellers directly; payment and collection are agreed between them.'),
        const SizedBox(height: 18),
        OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => const MarketWelcomePage(),
          )),
          icon: const Icon(Icons.waving_hand_outlined),
          label: const Text('View the welcome experience'),
        ),
        const SizedBox(height: 14),
        Text('Built for local discovery and direct contact. Listings are subject to marketplace moderation.',
          style: Theme.of(context).textTheme.bodySmall),
      ],
    ),
  );
}

class _AboutFeature extends StatelessWidget {
  const _AboutFeature({required this.icon, required this.title, required this.description});
  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: 44, height: 44,
        decoration: BoxDecoration(
          color: MarketPalette.mint.withValues(alpha: .55),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(icon, color: MarketPalette.forest),
      ),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 3),
        Text(description, style: Theme.of(context).textTheme.bodyMedium),
      ])),
    ]),
  );
}

class _WelcomePill extends StatelessWidget {
  const _WelcomePill({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
    decoration: BoxDecoration(
      color: Colors.white.withValues(alpha: .08),
      borderRadius: BorderRadius.circular(24),
      border: Border.all(color: Colors.white.withValues(alpha: .14)),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 16, color: MarketPalette.mint),
      const SizedBox(width: 6),
      Text(label, style: const TextStyle(color: Colors.white, fontSize: 12,
        fontWeight: FontWeight.w600)),
    ]),
  );
}

class _Orbit extends StatelessWidget {
  const _Orbit({required this.size, required this.opacity});
  final double size;
  final double opacity;

  @override
  Widget build(BuildContext context) => SizedBox.square(
    dimension: size,
    child: DecoratedBox(decoration: BoxDecoration(
      shape: BoxShape.circle,
      border: Border.all(color: MarketPalette.mint.withValues(alpha: opacity), width: 22),
    )),
  );
}
