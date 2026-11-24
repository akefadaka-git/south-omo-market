import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/features/seller/seller_access_page.dart';

void main() {
  group('Seller password validation', () {
    testWidgets('rejects fewer than six characters', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: MarketplaceHomePage(
          apiBaseUrl: 'https://market.example.test/api/v1',
          client: MockClient((_) async => http.Response('{}', 500)),
        ),
      ));

      await tester.tap(find.text('Create seller account'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('seller-display-name')), 'Test shop');
      await tester.enterText(find.byKey(const Key('seller-phone')), '0912345678');
      await tester.enterText(find.byKey(const Key('seller-password')), '12345');
      await tester.tap(find.text('Register and continue'));
      await tester.pumpAndSettle();

      expect(find.text('Password must be at least 6 characters'), findsOneWidget);
    });

    testWidgets('accepts exactly six characters and reaches the API flow',
        (tester) async {
      final requests = <String>[];
      final client = MockClient((request) async {
        requests.add(request.url.path);
        if (request.url.path.endsWith('/auth/register')) {
          return http.Response(jsonEncode({
            'id': 'synthetic-user-id',
            'phone_number': '0912345678',
            'display_name': 'Test shop',
          }), 201);
        }
        if (request.url.path.endsWith('/auth/login')) {
          return http.Response(jsonEncode({'access_token': 'synthetic-test-token'}), 200);
        }
        if (request.url.path.endsWith('/sellers/me')) {
          return http.Response(jsonEncode({'detail': 'Seller profile not found'}), 404);
        }
        return http.Response('{}', 404);
      });

      await tester.pumpWidget(MaterialApp(
        home: MarketplaceHomePage(
          apiBaseUrl: 'https://market.example.test/api/v1',
          client: client,
        ),
      ));

      await tester.tap(find.text('Create seller account'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('seller-display-name')), 'Test shop');
      await tester.enterText(find.byKey(const Key('seller-phone')), '0912345678');
      await tester.enterText(find.byKey(const Key('seller-password')), '123456');
      await tester.tap(find.text('Register and continue'));
      await tester.pumpAndSettle();

      expect(requests, contains('/api/v1/auth/register'));
      expect(requests, contains('/api/v1/auth/login'));
      expect(requests, contains('/api/v1/sellers/me'));
      expect(find.text('Password must be at least 6 characters'), findsNothing);
    });
  });
}
