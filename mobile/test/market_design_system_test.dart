import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/design/market_design_system.dart';

void main() {
  test('market theme exposes the branded primary and surface colors', () {
    final theme = MarketDesignSystem.lightTheme;
    expect(theme.colorScheme.primary, MarketPalette.forest);
    expect(theme.scaffoldBackgroundColor, MarketPalette.paper);
    expect(theme.useMaterial3, isTrue);
  });

  testWidgets('brand mark and abstract hero panel render', (tester) async {
    await tester.pumpWidget(MaterialApp(
      theme: MarketDesignSystem.lightTheme,
      home: const Scaffold(
        body: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            children: [
              MarketBrandMark(),
              MarketBrandPanel(
                title: 'Trade closer. Grow together.',
                subtitle: 'Goods, local skills and businesses.',
              ),
            ],
          ),
        ),
      ),
    ));

    expect(find.text('Trade closer. Grow together.'), findsOneWidget);
    expect(find.byType(MarketBrandMark), findsOneWidget);
  });
}