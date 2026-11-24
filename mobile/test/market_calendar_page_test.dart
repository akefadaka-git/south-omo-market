import 'dart:convert';

import 'package:flutter/material.dart';
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
      {'weekday': 0, 'weekday_name': 'Monday', 'markets': [{'name': 'Koybe'}]},
      {'weekday': 1, 'weekday_name': 'Tuesday', 'markets': [{'name': 'Asheker'}, {'name': 'Bala'}]},
      {'weekday': 2, 'weekday_name': 'Wednesday', 'markets': [{'name': 'Bobo'}]},
      {'weekday': 3, 'weekday_name': 'Thursday', 'markets': [{'name': 'Beneta'}]},
      {'weekday': 4, 'weekday_name': 'Friday', 'markets': []},
      {'weekday': 5, 'weekday_name': 'Saturday', 'markets': [{'name': 'Boshkoro'}, {'name': 'Ajo'}, {'name': 'Gento'}]},
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
}
