import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:south_omo_market/data/market_schedule_cache.dart';
import 'package:south_omo_market/features/marketplace/market_calendar_page.dart';

class MemoryMarketScheduleCache implements MarketScheduleCache {
  Map<String, dynamic>? value;

  @override
  Future<void> saveMarketSchedule(Map<String, dynamic> schedule) async {
    value = Map<String, dynamic>.from(schedule);
  }

  @override
  Future<Map<String, dynamic>?> cachedMarketSchedule() async =>
      value == null ? null : Map<String, dynamic>.from(value!);
}

void main() {
  final schedule = {
    'timezone': 'Africa/Addis_Ababa',
    'days': [
      {'weekday': 0, 'weekday_name': 'Monday', 'markets': [{'id': 'koybe', 'name': 'Koybe'}]},
      {'weekday': 1, 'weekday_name': 'Tuesday', 'markets': [{'id': 'asheker', 'name': 'Asheker'}, {'id': 'bala', 'name': 'Bala'}]},
      {'weekday': 2, 'weekday_name': 'Wednesday', 'markets': [{'id': 'bobo', 'name': 'Bobo'}]},
      {'weekday': 3, 'weekday_name': 'Thursday', 'markets': [{'id': 'beneta', 'name': 'Beneta'}]},
      {'weekday': 4, 'weekday_name': 'Friday', 'markets': []},
      {'weekday': 5, 'weekday_name': 'Saturday', 'markets': [{'id': 'boshkoro', 'name': 'Boshkoro'}, {'id': 'ajo', 'name': 'Ajo'}, {'id': 'gento', 'name': 'Gento'}]},
      {'weekday': 6, 'weekday_name': 'Sunday', 'markets': []},
    ],
  };

  testWidgets('weekly calendar renders the eight owner-provided market entries', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final cache = MemoryMarketScheduleCache();
    final client = MockClient((request) async {
      expect(request.url.path, endsWith('/markets/schedule'));
      expect(request.url.queryParameters['lang'], 'en');
      return http.Response(jsonEncode(schedule), 200);
    });
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      home: MarketCalendarPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        client: client,
        cache: cache,
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
    for (final name in ['Beneta', 'Asheker', 'Boshkoro', 'Bala', 'Koybe', 'Bobo', 'Ajo', 'Gento']) {
      expect(find.text(name), findsOneWidget);
    }
    expect(find.text('Saturday'), findsOneWidget);
    expect(find.text('Friday'), findsOneWidget);
    expect(cache.value?['timezone'], 'Africa/Addis_Ababa');
    client.close();
  });

  testWidgets('weekly calendar uses cached read-only schedule when offline', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final cache = MemoryMarketScheduleCache()..value = Map<String, dynamic>.from(schedule);
    final client = MockClient((request) async => http.Response('offline', 503));
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      home: MarketCalendarPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        client: client,
        cache: cache,
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.textContaining('Offline'), findsOneWidget);
    expect(find.text('Koybe'), findsOneWidget);
    expect(find.text('Gento'), findsOneWidget);
    client.close();
  });

  testWidgets('market calendar entry opens bilingual detail page with location map data', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final detail = {
      'id': 'market-koybe',
      'name': 'ቆይቤ ገበያ',
      'name_en': 'Koybe Market',
      'name_am': 'ቆይቤ ገበያ',
      'address': 'ቆይቤ ዋና መንገድ',
      'address_en': 'Main Road, Koybe',
      'address_am': 'ቆይቤ ዋና መንገድ',
      'description': 'የሳምንታዊ አካባቢ ገበያ',
      'latitude': 6.0,
      'longitude': 36.5,
      'location': {'name': 'ቆይቤ', 'name_en': 'Koybe', 'name_am': 'ቆይቤ'},
      'schedule_days': [0],
    };
    final cache = MemoryMarketScheduleCache();
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/markets/schedule')) {
        return http.Response(jsonEncode({
          'timezone': 'Africa/Addis_Ababa',
          'days': [
            {'weekday': 0, 'weekday_name': 'Monday', 'markets': [
              {'id': 'market-koybe', 'name': 'ቆይቤ ገበያ', 'name_en': 'Koybe Market', 'name_am': 'ቆይቤ ገበያ', 'location_id': 'town-koybe', 'schedule_days': [0]},
            ]},
          ],
        }), 200);
      }
      if (request.url.path.endsWith('/markets/market-koybe')) {
        expect(request.url.queryParameters['lang'], 'am');
        return http.Response(jsonEncode(detail), 200);
      }
      return http.Response('not found', 404);
    });
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('am'),
      supportedLocales: const [Locale('am'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      home: MarketCalendarPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        client: client,
        cache: cache,
      ),
    ));
    await tester.pumpAndSettle();
    // The fixture has one market on one day and fits in the configured test viewport.
    expect(find.byKey(const Key('market-calendar-entry-market-koybe')), findsOneWidget);
    expect(find.text('ቆይቤ ገበያ'), findsOneWidget);
    await tester.tap(find.byKey(const Key('market-calendar-entry-market-koybe')));
    await tester.pumpAndSettle();
    expect(find.text('ቆይቤ ዋና መንገድ'), findsOneWidget);
    expect(find.text('የአካባቢ ካርታ'), findsOneWidget);
    expect(find.text('6.0, 36.5'), findsOneWidget);
    client.close();
  });
}
