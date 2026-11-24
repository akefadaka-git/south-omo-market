import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/design/market_design_system.dart';

void main() {
  group('MarketListingCard', () {
    testWidgets('shows a local category fallback and clear listing hierarchy',
        (tester) async {
      var tapped = false;
      await tester.pumpWidget(MaterialApp(
        theme: MarketDesignSystem.lightTheme,
        home: Scaffold(
          body: MarketListingCard(
            title: 'Synthetic maize',
            location: 'Koybe',
            price: '1,250.00 ETB',
            category: 'Agriculture',
            onTap: () => tapped = true,
          ),
        ),
      ));

      expect(find.text('Synthetic maize'), findsOneWidget);
      expect(find.text('Koybe'), findsOneWidget);
      expect(find.text('1,250.00 ETB'), findsOneWidget);
      expect(find.text('Agriculture'), findsOneWidget);
      expect(find.byIcon(MarketIcons.agriculture), findsOneWidget);

      await tester.tap(find.text('Synthetic maize'));
      expect(tapped, isTrue);
    });

    testWidgets('renders a network image widget when a public image URL exists',
        (tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: MarketDesignSystem.lightTheme,
        home: Scaffold(
          body: MarketListingCard(
            title: 'Synthetic livestock',
            location: 'Jinka',
            price: '8,000.00 ETB',
            category: 'Livestock',
            imageUrl: 'https://market.example.test/api/v1/listings/1/images/2',
            onTap: () {},
          ),
        ),
      ));

      expect(find.byType(Image), findsOneWidget);
      expect(find.text('Synthetic livestock'), findsOneWidget);
    });
  });
}
