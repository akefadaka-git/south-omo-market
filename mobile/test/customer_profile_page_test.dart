import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:south_omo_market/features/marketplace/customer_profile_page.dart';

void main() {
  testWidgets('customer can load and save profile preferences through authenticated API', (tester) async {
    var patchPayload = <String, dynamic>{};
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/customers/me') && request.method == 'GET') {
        expect(request.headers['Authorization'], 'Bearer synthetic-token');
        return http.Response(jsonEncode({
          'id': 'profile-1',
          'user_id': 'user-1',
          'phone_number': '+251900000901',
          'display_name': 'Synthetic Buyer',
          'preferred_location_id': 'town-koybe',
          'preferred_market_id': 'market-koybe',
          'preferred_language': 'am',
          'email': 'buyer@example.test',
          'contact_preference': 'phone',
        }), 200);
      }
      if (request.url.path.endsWith('/customers/me') && request.method == 'PATCH') {
        expect(request.headers['Authorization'], 'Bearer synthetic-token');
        patchPayload = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({
          'id': 'profile-1',
          'user_id': 'user-1',
          'phone_number': '+251900000901',
          'display_name': patchPayload['display_name'],
          'preferred_location_id': patchPayload['preferred_location_id'],
          'preferred_market_id': patchPayload['preferred_market_id'],
          'preferred_language': patchPayload['preferred_language'],
          'email': patchPayload['email'],
          'contact_preference': patchPayload['contact_preference'],
        }), 200);
      }
      if (request.url.path.endsWith('/locations')) {
        return http.Response(jsonEncode([
          {'id': 'town-koybe', 'level': 'town', 'name': 'Koybe', 'name_en': 'Koybe'},
        ]), 200);
      }
      if (request.url.path.endsWith('/markets')) {
        return http.Response(jsonEncode([
          {'id': 'market-koybe', 'location_id': 'town-koybe', 'name': 'Koybe market'},
        ]), 200);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(
      home: CustomerProfilePage(
        apiBaseUrl: 'https://market.example.test/api/v1',
        accessToken: 'synthetic-token',
        client: client,
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Customer profile'), findsOneWidget);
    expect(find.byKey(const Key('customer-profile-name')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('customer-profile-name')), 'Updated Buyer');
    await tester.enterText(find.byKey(const Key('customer-profile-email')), 'updated@example.test');

    await tester.tap(find.byKey(const Key('save-customer-profile')));
    await tester.pumpAndSettle();

    expect(patchPayload['display_name'], 'Updated Buyer');
    expect(patchPayload['email'], 'updated@example.test');
    expect(patchPayload['preferred_location_id'], 'town-koybe');
    expect(patchPayload['preferred_market_id'], 'market-koybe');
    expect(find.text('Profile updated successfully.'), findsOneWidget);
    client.close();
  });

  testWidgets('customer sign out revokes the server session and returns to prior page', (tester) async {
    var logoutCalled = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/customers/me')) {
        return http.Response(jsonEncode({
          'id': 'profile-2',
          'user_id': 'user-2',
          'phone_number': '+251900000902',
          'display_name': 'Logout Buyer',
          'preferred_language': 'am',
        }), 200);
      }
      if (request.url.path.endsWith('/locations')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/markets')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/auth/logout') && request.method == 'POST') {
        expect(request.headers['Authorization'], 'Bearer logout-token');
        logoutCalled = true;
        return http.Response('', 204);
      }
      return http.Response('Not found', 404);
    });

    await tester.pumpWidget(MaterialApp(
      home: Builder(builder: (context) => Scaffold(
        body: TextButton(
          key: const Key('open-customer-profile'),
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => CustomerProfilePage(
              apiBaseUrl: 'https://market.example.test/api/v1',
              accessToken: 'logout-token',
              client: client,
            ),
          )),
          child: const Text('Open profile'),
        ),
      )),
    ));
    await tester.tap(find.byKey(const Key('open-customer-profile')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('customer-profile-logout')), findsOneWidget);
    await tester.tap(find.byKey(const Key('customer-profile-logout')));
    await tester.pumpAndSettle();

    expect(logoutCalled, isTrue);
    expect(find.text('Open profile'), findsOneWidget);
    client.close();
  });

o', (tester) async {
    var deleteCalled = false;
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/customers/me') && request.method == 'GET') {
        return http.Response(jsonEncode({
          'id': 'profile-photo', 'user_id': 'buyer-photo',
          'phone_number': '+251900000903', 'display_name': 'Photo Buyer',
          'preferred_language': 'am', 'profile_photo_url': '/customers/me/photo',
        }), 200);
      }
      if (request.url.path.endsWith('/locations')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/markets')) return http.Response('[]', 200);
      if (request.url.path.endsWith('/customers/me/photo') && request.method == 'DELETE') {
        expect(request.headers['Authorization'], 'Bearer photo-token');
        deleteCalled = true;
        return http.Response('', 204);
      }
      return http.Response('Not found', 404);
    });
    await tester.pumpWidget(MaterialApp(home: CustomerProfilePage(
      apiBaseUrl: 'https://market.example.test/api/v1',
      accessToken: 'photo-token', client: client,
    )));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('customer-profile-photo-pick')), findsOneWidget);
    await tester.tap(find.byKey(const Key('customer-profile-photo-remove')));
    await tester.pumpAndSettle();
    expect(deleteCalled, isTrue);
    expect(find.text('Profile photo removed.'), findsOneWidget);
    expect(find.byKey(const Key('customer-profile-photo-remove')), findsNothing);
    client.close();
  });
}
