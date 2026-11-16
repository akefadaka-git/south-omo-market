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
      if (request.url.path.endsWith('/auth/login')) {
        return http.Response(
          jsonEncode({'access_token': 'synthetic-access-token'}),
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
    expect(find.text('Seller sign in'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('seller-phone')), '+251900000001');
    await tester.enterText(
      find.byKey(const Key('seller-password')),
      'synthetic-test-password-123',
    );
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.text('Seller inquiry inbox'), findsOneWidget);
    expect(find.text('Synthetic goats'), findsOneWidget);
    expect(find.textContaining('+251900000001'), findsOneWidget);
    expect(find.text('Status: open'), findsOneWidget);

    await tester.tap(find.text('Mark read'));
    await tester.pumpAndSettle();
    expect(find.text('Status: read'), findsOneWidget);
  });
}
