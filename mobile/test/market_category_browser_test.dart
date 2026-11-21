import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/design/market_category_browser.dart';
import 'package:south_omo_market/design/market_design_system.dart';

void main() {
  testWidgets('category browser returns the selected subcategory ID', (tester) async {
    MarketCategorySelection? selected;
    await tester.pumpWidget(MaterialApp(
      theme: MarketDesignSystem.lightTheme,
      home: Builder(builder: (context) => Scaffold(body: TextButton(
        onPressed: () async {
          selected = await showModalBottomSheet<MarketCategorySelection>(
            context: context, isScrollControlled: true,
            builder: (_) => const MarketCategoryBrowserSheet(categories: [
              {'id': '00000000-0000-4000-8000-000000000002', 'name': 'Agriculture', 'parent_id': null},
              {'id': '30000000-0000-4000-8000-000000000005', 'name': 'Maize and grains',
               'parent_id': '00000000-0000-4000-8000-000000000002', 'is_leaf': true},
            ]),
          );
        },
        child: const Text('Open'),
      ))),
    ));
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    expect(find.text('Explore categories'), findsOneWidget);
    await tester.tap(find.text('Maize and grains'));
    await tester.pumpAndSettle();
    expect(selected?.categoryId, '30000000-0000-4000-8000-000000000005');
    expect(selected?.searchTerm, isNull);
  });

  testWidgets('category browser can clear the category filter', (tester) async {
    MarketCategorySelection? selected;
    await tester.pumpWidget(MaterialApp(
      theme: MarketDesignSystem.lightTheme,
      home: Builder(builder: (context) => Scaffold(body: TextButton(
        onPressed: () async {
          selected = await showModalBottomSheet<MarketCategorySelection>(
            context: context, isScrollControlled: true,
            builder: (_) => const MarketCategoryBrowserSheet(categories: [
              {'id': '00000000-0000-4000-8000-000000000001', 'name': 'Livestock'},
            ]),
          );
        },
        child: const Text('Open'),
      ))),
    ));
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('All categories'));
    await tester.pumpAndSettle();
    expect(selected?.categoryId, isNull);
    expect(selected?.searchTerm, isNull);
  });
}
