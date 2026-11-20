import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/design/market_brand_pages.dart';
import 'package:south_omo_market/design/market_icon_pack.dart';
import 'package:south_omo_market/design/market_design_system.dart';

void main() {
  test('brand icon pack resolves representative catalogue groups', () {
    expect(MarketIconPack.forCategory('Livestock'), MarketIconPack.livestock);
    expect(MarketIconPack.forCategory('Agriculture'), MarketIconPack.crops);
    expect(MarketIconPack.forCategory('Professional services'), MarketIconPack.services);
    expect(MarketIconPack.forCategory('Property rentals'), MarketIconPack.home);
  });

  testWidgets('about page exposes the welcome experience', (tester) async {
    await tester.pumpWidget(MaterialApp(
      theme: MarketDesignSystem.lightTheme,
      home: const MarketAboutPage(),
    ));
    expect(find.text('About South Omo Market'), findsOneWidget);
    expect(find.text('Welcome to a closer marketplace'), findsOneWidget);
    final welcomeButton = find.text('View the welcome experience');
    await tester.scrollUntilVisible(
      welcomeButton,
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(welcomeButton);
    await tester.pumpAndSettle();
    expect(find.text('Closer markets.\nStronger communities.'), findsOneWidget);
    expect(find.text('Explore the marketplace'), findsOneWidget);
  });
}
