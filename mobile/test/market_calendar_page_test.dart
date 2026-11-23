import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:sqflite/sqflite.dart' as sqflite;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:south_omo_market/data/local_draft_store.dart';
import 'package:south_omo_market/features/marketplace/market_calendar_page.dart';

Future<void> pumpAfterIo(WidgetTester tester) async {
  await tester.runAsync(() async {
    await Future<void>.delayed(const Duration(milliseconds: 500));
  });
  await tester.pump();
}

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    sqflite.databaseFactory = databaseFactoryFfi;
  });

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

  testWidgets('weekly calendar loads the eight owner-provided market entries', (tester) async {
    final directory = await Directory.systemTemp.createTemp('market-calendar');
    final store = LocalDraftStore(databasePath: '${directory.path}/schedule.db');
    final client = MockClient((request) async {
      expect(request.url.path, endsWith('/markets/schedule'));
      return http.Response(jsonEncode(schedule), 200);
    });
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      home: MarketCalendarPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        client: client,
        store: store,
      ),
    ));
    await pumpAfterIo(tester);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    for (final name in ['Beneta', 'Asheker', 'Boshkoro', 'Bala', 'Koybe', 'Bobo', 'Ajo', 'Gento']) {
      await tester.scrollUntilVisible(find.text(name), 250, scrollable: find.byType(Scrollable).last);
      expect(find.text(name), findsOneWidget);
    }
    await tester.scrollUntilVisible(find.text('Saturday'), 250, scrollable: find.byType(Scrollable).last);
    expect(find.text('Saturday'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Friday'), -250, scrollable: find.byType(Scrollable).last);
    expect(find.text('Friday'), findsOneWidget);
    await store.close();
    await directory.delete(recursive: true);
    client.close();
  });

  testWidgets('weekly calendar falls back to cached read-only schedule offline', (tester) async {
    final directory = await Directory.systemTemp.createTemp('market-calendar-offline');
    final path = '${directory.path}/schedule.db';
    final seeded = LocalDraftStore(databasePath: path);
    await seeded.saveMarketSchedule(schedule);
    await seeded.close();

    final store = LocalDraftStore(databasePath: path);
    final client = MockClient((request) async => http.Response('offline', 503));
    await tester.pumpWidget(MaterialApp(
      locale: const Locale('en'),
      home: MarketCalendarPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        client: client,
        store: store,
      ),
    ));
    await pumpAfterIo(tester);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.textContaining('Offline'), findsOneWidget);
    expect(find.text('Koybe'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Gento'), 250, scrollable: find.byType(Scrollable).last);
    expect(find.text('Gento'), findsOneWidget);
    await store.close();
    await directory.delete(recursive: true);
    client.close();
  });
}
