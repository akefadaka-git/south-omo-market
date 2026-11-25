import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:south_omo_market/features/marketplace/seller_listing_pages.dart';

void main() {
  testWidgets('seller onboarding submits business category, locality and privacy settings', (tester) async {
    Map<String, dynamic>? submitted;
    var completed = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/categories')) {
        return http.Response(jsonEncode([
          {'id': 'category-local-produce', 'name': 'Local produce', 'is_leaf': true},
        ]), 200);
      }
      if (request.url.path.endsWith('/locations')) {
        return http.Response(jsonEncode([
          {'id': 'town-koybe', 'level': 'town', 'name': 'Koybe'},
        ]), 200);
      }
      if (request.url.path.endsWith('/sellers/me') && request.method == 'GET') {
        return http.Response('{"detail":"Seller profile not found"}', 404);
      }
      if (request.url.path.endsWith('/sellers/me') && request.method == 'POST') {
        submitted = jsonDecode(request.body) as Map<String, dynamic>;
        expect(request.headers['Authorization'], 'Bearer synthetic-seller-token');
        return http.Response(jsonEncode({
          'id': 'seller-profile-1',
          'business_id': 'business-1',
          'public_name': submitted!['public_name'],
          'business_status': 'active',
          'verification_status': 'pending',
          'membership_status': 'pending',
        }), 201);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(
      home: SellerProfileSetupPage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        accessToken: 'synthetic-seller-token',
        client: client,
        onComplete: () => completed = true,
      ),
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('seller-business-name')), 'Koybe Produce');
    await tester.tap(find.byKey(const Key('seller-business-category')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Local produce').last);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('seller-business-location')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Koybe').last);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('seller-business-save')));
    await tester.pumpAndSettle();

    expect(completed, isTrue);
    expect(submitted?['public_name'], 'Koybe Produce');
    expect(submitted?['business_type'], 'individual');
    expect(submitted?['primary_category_id'], 'category-local-produce');
    expect(submitted?['operating_location_id'], 'town-koybe');
    expect(submitted?['public_location_visibility'], 'hidden');
    expect(submitted?['publish_contact_phone'], isFalse);
    client.close();
  });
}
