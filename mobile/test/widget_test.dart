import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/main.dart';

void main() {
  testWidgets('seller can sign in and manage an inquiry', (tester) async {
    var inquiryStatus = 'open';
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/categories')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/listings')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response(
          jsonEncode({'access_token': 'synthetic-access-token'}),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path.endsWith('/sellers/me') && request.method == 'GET') {
        return http.Response(
          jsonEncode({'id': 'seller-1', 'public_name': 'Synthetic Seller', 'location': 'Koybe'}),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path.endsWith('/inquiries/inbox') && request.method == 'GET') {
        return http.Response(
          jsonEncode([
            {
              'id': 'synthetic-inquiry-id',
              'listing_id': 'synthetic-listing-id',
              'listing_title': 'Synthetic goats',
              'buyer_name': 'Synthetic Buyer',
              'buyer_contact': '+251900000001',
              'message': 'Are these available?',
              'status': inquiryStatus,
            }
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path.endsWith('/synthetic-inquiry-id/status') &&
          request.method == 'PATCH') {
        inquiryStatus = (jsonDecode(request.body) as Map<String, dynamic>)['status'] as String;
        return http.Response(
          jsonEncode({'id': 'synthetic-inquiry-id', 'status': inquiryStatus}),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(SouthOmoMarketApp(
      apiBaseUrl: 'https://market.example.test/api/v1',
      client: client,
    ));
    await tester.pumpAndSettle();
    expect(find.text('ደቡብ ኦሞ ገበያ'), findsOneWidget);
    await tester.tap(find.byTooltip('የሻጭ መግቢያ'));
    await tester.pumpAndSettle();
    expect(find.text('የሻጭ መግቢያ'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('seller-phone')), '+251900000001');
    await tester.enterText(
      find.byKey(const Key('seller-password')),
      'synthetic-test-password-123',
    );
    await tester.tap(find.text('ግባ'));
    await tester.pumpAndSettle();

    expect(find.text('የሻጭ ጥያቄዎች'), findsOneWidget);
    expect(find.text('Synthetic goats'), findsOneWidget);
    expect(find.textContaining('+251900000001'), findsOneWidget);
    expect(find.text('ሁኔታ: ክፍት'), findsOneWidget);

    await tester.tap(find.text('እንደተነበበ ምልክት አድርግ'));
    await tester.pumpAndSettle();
    expect(find.text('ሁኔታ: ተነብቧል'), findsOneWidget);
  });
  testWidgets('new account completes seller profile onboarding before inbox', (tester) async {
    var profileCreated = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response(jsonEncode({'access_token': 'synthetic-token'}), 200);
      }
      if (request.url.path.endsWith('/sellers/me') && request.method == 'GET') {
        return profileCreated
          ? http.Response(jsonEncode({'id': 'seller-1'}), 200)
          : http.Response('Not found', 404);
      }
      if (request.url.path.endsWith('/sellers/me') && request.method == 'POST') {
        profileCreated = true;
        return http.Response(jsonEncode({'id': 'seller-1'}), 201);
      }
      if (request.url.path.endsWith('/inquiries/inbox')) {
        return http.Response('[]', 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(SouthOmoMarketApp(
      apiBaseUrl: 'https://market.example.test/api/v1',
      client: client,
    ));
    await tester.pumpAndSettle();
    expect(find.text('South Omo Market'), findsOneWidget);
    await tester.tap(find.byTooltip('Seller sign in'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('seller-phone')), '+251900000009');
    await tester.enterText(find.byKey(const Key('seller-password')), 'synthetic-test-password-123');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('የሻጭ መገለጫ ያዘጋጁ'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'Synthetic Shop');
    await tester.enterText(find.byType(TextField).last, 'Koybe');
    await tester.tap(find.text('የሻጭ መገለጫ ፍጠር'));
    await tester.pumpAndSettle();
    expect(profileCreated, isTrue);
    expect(find.text('የሻጭ ጥያቄዎች'), findsOneWidget);
    client.close();
  });

}
