import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:south_omo_market/design/market_category_browser.dart';
import 'package:south_omo_market/l10n/market_strings.dart';

void main() {
  testWidgets('Amharic category browser localizes its navigation and livestock topics', (tester) async {
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('am'),
      supportedLocales: const [Locale('am'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: Builder(builder: (context) => Scaffold(
        body: Center(child: ElevatedButton(
          onPressed: () => showModalBottomSheet<void>(
            context: context,
            builder: (_) => const MarketCategoryBrowserSheet(
              categories: [
                {'id': '00000000-0000-4000-8000-000000000001', 'name': 'እንስሳት', 'parent_id': null},
                {'id': '30000000-0000-4000-8000-000000000001', 'name': 'ከብቶችና ላሞች',
                 'parent_id': '00000000-0000-4000-8000-000000000001', 'is_leaf': true},
                {'id': '30000000-0000-4000-8000-000000000002', 'name': 'ፍየሎችና በጎች',
                 'parent_id': '00000000-0000-4000-8000-000000000001', 'is_leaf': true},
              ],
            ),
          ),
          child: const Text('open'),
        )),
      )),
    ));
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    expect(find.text('ምድቦችን ይመልከቱ'), findsOneWidget);
    expect(find.text('ሁሉም ምድቦች'), findsOneWidget);
    expect(find.text('ከብቶችና ላሞች'), findsOneWidget);
    expect(find.text('ፍየሎችና በጎች'), findsOneWidget);
  });

  testWidgets('market status labels are localized in Amharic', (tester) async {
    late String label;
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('am'),
      supportedLocales: const [Locale('am'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: Builder(builder: (context) {
        label = marketStatusLabel(context, 'pending_review');
        return const SizedBox.shrink();
      }),
    ));
    expect(label, 'ግምገማ በመጠባበቅ ላይ');
  });
  testWidgets('Maale strings fall back to English until reviewed translations exist', (tester) async {
    late String submitLabel;
    late String statusLabel;
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('mdy'),
      supportedLocales: const [Locale('mdy'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: Builder(builder: (context) {
        submitLabel = marketString(context, en: 'Submit report', am: 'ሪፖርት ላክ', mdy: '');
        statusLabel = marketStatusLabel(context, 'in_review');
        return const SizedBox.shrink();
      }),
    ));
    expect(submitLabel, 'Submit report');
    expect(statusLabel, 'Under review');
  });

}
