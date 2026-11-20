import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:south_omo_market/main.dart';

void main() {
  testWidgets('Amharic branded splash is the initial route', (tester) async {
    final client = MockClient((request) async => http.Response('[]', 200));
    await tester.pumpWidget(SouthOmoMarketApp(
      apiBaseUrl: 'https://market.example/api/v1',
      client: client,
    ));

    expect(find.text('ደቡብ ኦሞ ገበያ'), findsOneWidget);
    expect(find.text('ከአካባቢ ለአካባቢ'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 2100));
    await tester.pumpAndSettle();

    expect(find.text('ምርቶችን እና አገልግሎቶችን ፈልግ'), findsOneWidget);
    expect(find.text('South Omo Market'), findsNothing);
  });
  testWidgets('seller registration is discoverable in Amharic', (tester) async {
    final client = MockClient((request) async => http.Response('[]', 200));
    await tester.pumpWidget(SouthOmoMarketApp(
      apiBaseUrl: 'https://market.example/api/v1',
      client: client,
    ));
    await tester.pump(const Duration(milliseconds: 2100));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('የሻጭ መግቢያ'));
    await tester.pumpAndSettle();

    expect(find.text('የሻጭ መለያ ፍጠር'), findsOneWidget);
    await tester.tap(find.text('የሻጭ መለያ ፍጠር'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('seller-display-name')), findsOneWidget);
  });

  testWidgets('Amharic is default and English is an explicit language choice', (tester) async {
    final client = MockClient((request) async => http.Response('[]', 200));
    await tester.pumpWidget(SouthOmoMarketApp(
      apiBaseUrl: 'https://market.example/api/v1',
      client: client,
    ));
    await tester.pump(const Duration(milliseconds: 2100));
    await tester.pumpAndSettle();

    expect(find.text('ደቡብ ኦሞ ገበያ'), findsOneWidget);
    expect(find.byTooltip('ቋንቋ ቀይር'), findsOneWidget);
    await tester.tap(find.byTooltip('ቋንቋ ቀይር'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();

    expect(find.text('Search products and services'), findsOneWidget);
    client.close();
  });

}
